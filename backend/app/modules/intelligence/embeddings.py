"""
Local embedding provider (Phase 11) - implements the existing EmbeddingProvider abstraction with NO external API.

It is a deterministic *hashed lexical-semantic* vector, not a neural model: word uni/bi-grams and character
tri-grams are hashed into 256 buckets after a small HCME synonym expansion (accumulator -> battery, lubricant -> oil)
and electrical specs are normalised (24V -> v24, 100A -> a100). It ranks "24V starter motor" near parts whose real name
or description says so, and it is reproducible in tests.
It does not understand meaning it has no vocabulary for. Swapping in a neural model later only needs another
EmbeddingProvider subclass with the same interface.
"""
import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import List, Optional

from app.modules.intelligence.providers import EmbeddingProvider

logger = logging.getLogger("hcme_backend")

DIMS = 256
_STOP = {"the", "a", "an", "of", "for", "and", "or", "with", "to", "in", "on", "at", "is", "are", "be", "need",
         "hitachi", "oem", "genuine", "demo", "part", "parts", "unit", "units", "pcs", "required", "within"}
# HCME domain synonyms: token -> extra tokens that carry the same meaning
_SYNONYMS = {"accumulator": ["battery"], "accu": ["battery"], "lubricant": ["oil"], "hydraulics": ["hydraulic"]}


def normalise_specs(text: str) -> str:
    """24V -> v24, 100A -> a100 so electrical specs stated in part names match exactly."""
    t = text.lower()
    t = re.sub(r"(\d+(?:\.\d+)?)\s*v(?:dc)?\b", r" v\1 ", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*a(?:mps?)?\b", r" a\1 ", t)
    return t


def _bucket(token: str) -> int:
    return int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % DIMS


def tokens(text: str) -> List[str]:
    out: List[str] = []
    for w in re.findall(r"[a-z0-9]+", normalise_specs(text or "")):
        if w in _STOP:
            continue
        out.append(w)
        out.extend(_SYNONYMS.get(w, []))
    return out


@lru_cache(maxsize=4096)
def _embed_cached(text: str) -> tuple:
    words = tokens(text)
    feats: dict = {}

    def add(key: str, weight: float) -> None:
        feats[key] = feats.get(key, 0.0) + weight

    for w in words:
        add("w:" + w, 1.0)
        # electrical spec tokens (v24, a100) are exact-match features: weight them up
        if re.fullmatch(r"(v|a)\d+(\.\d+)?", w):
            add("s:" + w, 1.5)
        else:
            padded = f"^{w}$"
            for i in range(len(padded) - 2):
                add("c:" + padded[i:i + 3], 0.3)
    for a, b in zip(words, words[1:]):
        add("b:" + a + "_" + b, 0.6)
    vec = [0.0] * DIMS
    for k, v in feats.items():
        vec[_bucket(k)] += 1.0 + math.log(v) if v > 1 else v
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return tuple(round(x / norm, 6) for x in vec)


class LocalEmbeddingProvider(EmbeddingProvider):
    """Always available, offline, deterministic."""

    def is_available(self) -> bool:
        return True

    def embed(self, text: str) -> Optional[List[float]]:
        try:
            return list(_embed_cached(text or ""))
        except Exception as exc:  # never let an embedding failure break a request
            logger.warning("Local embedding failed: %s", exc)
            return None

    @property
    def dimensions(self) -> int:
        return DIMS


_provider = LocalEmbeddingProvider()


def embed(text: str) -> Optional[List[float]]:
    return _provider.embed(text)


def cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
