import os
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("NODE_ENV", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Neo4j — sole runtime database
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "")

    # No hard-coded fallback: a default that lives in the source is a default anyone can read (and forge tokens with).
    # If JWT_SECRET is not set, a random per-process secret is used instead - tokens then last only until a restart.
    JWT_SECRET: str = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
    JWT_ALGORITHM: str = "HS256"
    TEST_AUTH_ENABLED: bool = os.getenv("TEST_AUTH_ENABLED", "true").lower() == "true"

    # Visitor analytics dashboard - one shared admin password, not a per-user account system
    ANALYTICS_ADMIN_PASSWORD: str = os.getenv("ANALYTICS_ADMIN_PASSWORD", "")

    AVAILABILITY_FRESHNESS_TTL_SECONDS: int = int(
        os.getenv("AVAILABILITY_FRESHNESS_TTL_SECONDS", "3600")
    )

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Parts Intelligence — Gemini LLM provider (query understanding +
    # evidence explanation only; never fitment/availability/pricing/
    # allocation/order/shipment/approval decisions). Optional: if unset,
    # the module falls back to DeterministicLLMProvider.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
