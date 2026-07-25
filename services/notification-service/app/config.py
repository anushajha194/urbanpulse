"""
Configuration settings for the notification service.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Notification service settings."""

    # --- Queue ---
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    INPUT_QUEUE: str = Field(
        default="notification_jobs",
        description="Queue to consume notification tasks from",
    )

    # --- Templates ---
    TEMPLATES_DIR: str = Field(
        default="app/templates",
        description="Path to text templates directory",
    )

    # --- Twilio SMS Provider Config ---
    TWILIO_ACCOUNT_SID: str = Field(default="")
    TWILIO_AUTH_TOKEN: str = Field(default="")
    TWILIO_FROM_NUMBER: str = Field(default="+12345678901")

    # --- Worker parameters ---
    WORKER_POLL_TIMEOUT: int = Field(default=5)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
