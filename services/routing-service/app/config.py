"""
Configuration settings for the routing and SLA service.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Routing service settings."""

    # --- Rules Path ---
    ROUTING_RULES_PATH: str = Field(
        default="app/routing_rules.json",
        description="Path to JSON configuration for routing and SLA mappings",
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
        default="routing_jobs",
        description="Queue to consume routing tasks from",
    )
    NOTIFICATION_QUEUE: str = Field(
        default="notification_jobs",
        description="Queue to publish notification alerts to",
    )

    # --- Worker parameters ---
    WORKER_POLL_TIMEOUT: int = Field(default=5)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
