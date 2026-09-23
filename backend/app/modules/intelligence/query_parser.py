"""
backend/app/modules/intelligence/query_parser.py

Turns a free-text query into a ParsedIntent using the configured
LLMProvider (real or deterministic fallback — see providers.py).

If the configured provider is a real LLM (e.g. Gemini) and the call
fails (timeout, network error, bad response, etc.), this degrades to the
deterministic parser rather than propagating the failure — natural-language
search must keep working even when the LLM is unavailable.
"""

from app.logging_config.logger import logger
from app.modules.intelligence.providers import DeterministicLLMProvider, get_llm_provider
from app.modules.intelligence.schemas import ParsedIntent


def parse_query(query: str) -> ParsedIntent:
    provider = get_llm_provider()
    try:
        return provider.parse_intent(query)
    except Exception as e:
        if isinstance(provider, DeterministicLLMProvider):
            raise
        logger.warning(f"Parts Intelligence LLM query parsing degraded, falling back to deterministic: {e}")
        return DeterministicLLMProvider().parse_intent(query)
