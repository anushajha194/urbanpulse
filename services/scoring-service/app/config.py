"""
Configuration settings for the scoring service.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Scoring service settings."""

    # --- Rules File ---
    SCORING_RULES_PATH: str = Field(
        default="app/scoring_rules.json",
        description="Path to JSON configuration file for scoring weights",
    )

    # --- Database & Queue ---
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/urbanpulse",
        description="PostgreSQL connection string",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    INPUT_QUEUE: str = Field(
        default="scoring_jobs",
        description="Queue to consume scoring jobs from",
    )

    # --- Worker poll ---
    WORKER_POLL_TIMEOUT: int = Field(default=5)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
