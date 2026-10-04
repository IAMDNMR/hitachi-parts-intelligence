"""
backend/app/modules/intelligence/providers.py

LLMProvider / EmbeddingProvider abstraction.

No vendor lock-in: any real provider (Anthropic, OpenAI, etc.) can be
plugged in by implementing these two interfaces. No API keys are hardcoded
here or anywhere in this module — a key is read only from environment
variables via app.config, and only inside the concrete provider that needs
it.

Dev/test path: if no LLM credentials are configured, `get_llm_provider()`
returns `DeterministicLLMProvider`, which does NOT call any external
service and does NOT pretend to be a real model. It uses simple pattern
matching to extract a plausible machine model token and the remaining
free text as the part requirement. This keeps natural-language search
usable in every environment without fabricating AI output.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.modules.intelligence.schemas import Evidence, ParsedIntent


class LLMProvider(ABC):
    @abstractmethod
    def parse_intent(self, query: str) -> ParsedIntent:
        ...

    @abstractmethod
    def explain(self, part: Dict, evidence: List[Evidence]) -> str:
        """Generate a user-friendly explanation from ALREADY-VERIFIED
        graph/business evidence. Must never be used to decide fitment,
        availability, pricing, or any transactional outcome — the evidence
        passed in is the sole source of truth; this only phrases it."""
        ...


class EmbeddingProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def embed(self, text: str) -> Optional[List[float]]:
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...


# ---------------------------------------------------------------------------
# Deterministic dev/test implementations — no external calls, no fabricated
# "AI" output. These are explicitly labelled as non-LLM in ParsedIntent.source.
# ---------------------------------------------------------------------------

_MODEL_PATTERN = re.compile(r"\b([A-Z]{1,4}\d{1,4}[A-Z0-9\-]*)\b")


class DeterministicLLMProvider(LLMProvider):
    """Pattern-based fallback used when no LLM credentials are configured.

    This is NOT a language model. It extracts a token that looks like a
    machine model code (letters+digits, e.g. ZX210-7) and treats the
    remainder of the query as the part requirement text. It is
    intentionally simple and deterministic so tests are reproducible.
    """

    def parse_intent(self, query: str) -> ParsedIntent:
        model_match = _MODEL_PATTERN.search(query.upper())
        machine_model = model_match.group(1) if model_match else None
        remainder = query
        if model_match:
            remainder = (query[: model_match.start()] + query[model_match.end():]).strip()
        remainder = re.sub(r"\b(for|the|a|an|i need|need|please|find|me)\b", "", remainder, flags=re.IGNORECASE)
        remainder = re.sub(r"\s+", " ", remainder).strip(" .,-")
        return ParsedIntent(
            intent="find_part",
            machine_model=machine_model,
            part_requirement=remainder or None,
            raw_query=query,
            source="deterministic",
        )

    def explain(self, part: Dict, evidence: List[Evidence]) -> str:
        from app.modules.intelligence.explanation import build_explanation_text
        return build_explanation_text(part, evidence)


# ---------------------------------------------------------------------------
# Gemini provider — real LLM. Strictly limited to (a) query understanding
# / intent extraction and (b) phrasing already-verified evidence. It is
# NEVER consulted for fitment, availability, inventory, pricing, fulfilment,
# allocation, order, shipment, service completion, or approval/replacement
# decisions — those remain purely graph/business-rule driven in fitment.py,
# search.py, alternatives.py, service.py.
# ---------------------------------------------------------------------------

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_TIMEOUT_SECONDS = 8.0


class GeminiProviderError(RuntimeError):
    """Raised on any Gemini API failure (network, timeout, non-2xx, bad
    payload). Callers must catch this and degrade gracefully — never let it
    propagate outside the intelligence module."""


class _GeminiBudget:
    """Process-wide request budget for the Gemini free tier (15 requests per
    minute). A call is refused immediately — so callers fall back to the
    deterministic path without waiting — when the last-minute window is full,
    or during a cooldown after Google answers 429."""

    def __init__(self, per_minute: int):
        import threading
        self.per_minute = per_minute
        self.calls: List[float] = []
        self.cooldown_until = 0.0
        self.lock = threading.Lock()

    def acquire(self) -> bool:
        import time
        now = time.monotonic()
        with self.lock:
            if now < self.cooldown_until:
                return False
            self.calls = [t for t in self.calls if now - t < 60]
            if len(self.calls) >= self.per_minute:
                return False
            self.calls.append(now)
            return True

    def rate_limited(self, seconds: float = 60.0) -> None:
        import time
        with self.lock:
            self.cooldown_until = time.monotonic() + seconds


# Free-tier models tried in order; each has its own per-minute budget. Override
# with GEMINI_MODELS="model-a,model-b". GEMINI_MODEL (if set) is tried first.
_FREE_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_MODELS", "gemini-flash-lite-latest,gemini-3.1-flash-lite,gemini-3.8-flash").split(",") if m.strip()]
_RPM = {"gemini-3.8-flash": 4}
_BUDGETS: Dict[str, "_GeminiBudget"] = {}


def _budget(model: str) -> "_GeminiBudget":
    if model not in _BUDGETS:
        _BUDGETS[model] = _GeminiBudget(_RPM.get(model, int(os.getenv("GEMINI_RPM_LIMIT", "14"))))
    return _BUDGETS[model]


class GeminiLLMProvider(LLMProvider):
    """Calls the real Gemini generateContent REST API directly via httpx
    (consistent with the rest of this module — no new SDK dependency). The
    API key is read once from app.config.settings (never hardcoded, never
    logged)."""

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def _generate(self, system: str, user: str, json_mode: bool = False, timeout: float = GEMINI_TIMEOUT_SECONDS) -> str:
        import httpx

        body: Dict = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            # Minimal thinking keeps latency low (~1.5s) — the model only parses
            # questions and phrases verified evidence, it does no reasoning of its own.
            "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingLevel": "minimal"}},
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        import time as _time
        deadline = _time.monotonic() + timeout
        models = [self._model] + [m for m in _FREE_MODELS if m != self._model]
        last_error = "no free Gemini model has request budget left"
        for model in models:
            remaining = deadline - _time.monotonic()
            if remaining < 0.8:
                break
            budget = _budget(model)
            if not budget.acquire():
                continue
            try:
                with httpx.Client(timeout=remaining) as client:
                    resp = client.post(f"{GEMINI_API_BASE}/{model}:generateContent",
                                       params={"key": self._api_key}, json=body)
            except Exception as e:
                # Timed out: this model is overloaded right now — rest it and stop.
                budget.rate_limited(30)
                last_error = f"{model}: {type(e).__name__}"
                break
            if resp.status_code in (429, 503):
                # Rate-limited or overloaded: rest this model, try the next one.
                budget.rate_limited(60)
                last_error = f"{model}: HTTP {resp.status_code}"
                continue
            if resp.status_code == 400 and "thinkingConfig" in body["generationConfig"]:
                # Some models reject thinkingLevel — retry this model once without it.
                slim = {**body, "generationConfig": {k: v for k, v in body["generationConfig"].items() if k != "thinkingConfig"}}
                try:
                    with httpx.Client(timeout=max(deadline - _time.monotonic(), 0.8)) as client:
                        resp = client.post(f"{GEMINI_API_BASE}/{model}:generateContent",
                                           params={"key": self._api_key}, json=slim)
                except Exception as e:
                    last_error = f"{model}: {type(e).__name__}"
                    break
            if resp.status_code != 200:
                # Never include the request (it carries the key) in the message.
                last_error = f"{model}: HTTP {resp.status_code}"
                continue
            try:
                self.last_model = model
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_error = f"{model}: bad payload {type(e).__name__}"
        raise GeminiProviderError(f"Gemini API call failed: {last_error}")

    def parse_intent(self, query: str) -> ParsedIntent:
        system = (
            "You extract structured search intent from a free-text spare "
            "parts request for heavy machinery. Return JSON only, with "
            "exactly these keys: "
            '"machine_model" (string or null, e.g. "ZX210-7"), '
            '"part_requirement" (string or null, the part being requested, '
            "with the machine model removed). "
            "Extract only what is explicitly present in the user's request. "
            "Do not invent part numbers, machine models, availability, "
            "pricing, or relationships. Use null for anything not present "
            "in the text — do not guess. You are NOT deciding whether the "
            "part exists, fits, or is available — you are only parsing the "
            "user's text."
        )
        content = self._generate(system, query, json_mode=True)
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError) as e:
            raise GeminiProviderError(f"Gemini returned non-JSON intent payload: {e}") from e

        machine_model = parsed.get("machine_model") or None
        part_requirement = parsed.get("part_requirement") or None
        return ParsedIntent(
            intent="find_part",
            machine_model=machine_model,
            part_requirement=part_requirement,
            raw_query=query,
            source="llm",
        )

    def explain(self, part: Dict, evidence: List[Evidence]) -> str:
        evidence_lines = "\n".join(f"- {e.kind}: {e.detail}" for e in evidence)
        system = (
            "You write a short, user-friendly explanation (1-2 sentences) "
            "for why a spare part matched a search. Return plain text only. "
            "You MUST rely only on the verified evidence given below — it "
            "has already been checked against the graph/business rules. Do "
            "NOT invent fitment, availability, pricing, or any fact not "
            "present in the evidence. Do not claim the part is confirmed "
            "available or approved unless the evidence says so. If the "
            "evidence marks something UNKNOWN, keep it UNKNOWN in your "
            "wording — never imply it became confirmed, available, "
            "approved, or fitted."
        )
        user = (
            f"Part: {part.get('part_name', 'Unknown part')} "
            f"({part.get('part_number') or part.get('part_id')})\n"
            f"Verified evidence:\n{evidence_lines}"
        )
        content = self._generate(system, user)
        return content.strip()


class GroqLLMProvider(GeminiLLMProvider):
    """Groq (OpenAI-compatible chat completions). Reuses the Gemini provider's
    prompts; only the transport differs. Key comes from GROQ_API_KEY."""

    def _generate(self, system: str, user: str, json_mode: bool = False, timeout: float = GEMINI_TIMEOUT_SECONDS) -> str:
        import httpx

        body: Dict = {
            "model": self._model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post("https://api.groq.com/openai/v1/chat/completions",
                                   headers={"Authorization": f"Bearer {self._api_key}"}, json=body)
        except Exception as e:
            raise GeminiProviderError(f"Groq API call failed: {type(e).__name__}") from e
        if resp.status_code != 200:
            raise GeminiProviderError(f"Groq API call failed: HTTP {resp.status_code}")
        try:
            self.last_model = self._model
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise GeminiProviderError(f"Groq bad payload {type(e).__name__}") from e


class NullEmbeddingProvider(EmbeddingProvider):
    """No embedding backend configured. Semantic search degrades to lexical."""

    def is_available(self) -> bool:
        return False

    def embed(self, text: str) -> Optional[List[float]]:
        return None

    @property
    def dimensions(self) -> int:
        return 0


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

def get_llm_provider() -> LLMProvider:
    """Return a real LLM provider if credentials are configured, else the
    deterministic dev/test provider. No API key is ever logged or embedded
    in code."""
    from app.config import settings

    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and (os.getenv("LLM_PROVIDER", "").lower() == "groq" or not settings.GEMINI_API_KEY):
        return GroqLLMProvider(api_key=groq_key, model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))
    if settings.GEMINI_API_KEY:
        return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    return DeterministicLLMProvider()


def get_embedding_provider() -> EmbeddingProvider:
    """Return a real embedding provider if credentials are configured, else
    NullEmbeddingProvider. No embedding provider is currently configured in
    this environment, so this always returns NullEmbeddingProvider today."""
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"):
        return NullEmbeddingProvider()
    return NullEmbeddingProvider()
