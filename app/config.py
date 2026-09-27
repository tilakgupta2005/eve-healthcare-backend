"""
Centralized application configuration.

All settings are sourced from environment variables (with sane local
defaults) so the same codebase runs unchanged against SQLite (quick local
dev) or PostgreSQL (docker-compose / production), per the assignment's
"PostgreSQL preferred" guidance.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "EVE Healthcare - Diagnostics Booking API"
    environment: str = "development"

    # --- Database ---
    # Example postgres URL: postgresql+psycopg2://user:pass@db:5432/eve_healthcare
    database_url: str = "sqlite:///./eve_healthcare.db"

    # --- Auth / JWT ---
    secret_key: str = "insecure-dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h, convenient for reviewers

    # --- Payments (simulation) ---
    # Probability [0-1] that a simulated payment succeeds when the caller
    # does not force an outcome. Kept configurable so behaviour is
    # deterministic in tests (see tests/conftest.py).
    payment_success_rate: float = 0.8


settings = Settings()
