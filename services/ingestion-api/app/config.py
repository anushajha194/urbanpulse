"""
Application configuration via environment variables.

Uses pydantic-settings for type-safe config with defaults suitable for local dev.
All settings can be overridden via environment variables or a .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Ingestion API configuration."""

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/urbanpulse",
        description="PostgreSQL connection string",
    )
    DB_POOL_MIN: int = Field(default=2, description="Minimum DB pool connections")
    DB_POOL_MAX: int = Field(default=10, description="Maximum DB pool connections")

    # --- S3 / MinIO ---
    S3_ENDPOINT: str = Field(
        default="http://localhost:9000", description="S3-compatible endpoint URL"
    )
    S3_BUCKET: str = Field(
        default="urbanpulse-images", description="Image storage bucket name"
    )
    S3_ACCESS_KEY: str = Field(default="minioadmin", description="S3 access key")
    S3_SECRET_KEY: str = Field(default="minioadmin", description="S3 secret key")
    S3_REGION: str = Field(default="us-east-1", description="S3 region")

    # --- Redis Queue ---
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    QUEUE_NAME: str = Field(
        default="detection_jobs", description="Queue name for detection jobs"
    )

    # --- Image Processing ---
    MAX_IMAGE_SIZE_MB: int = Field(default=20, description="Max upload size in MB")
    ALLOWED_CONTENT_TYPES: list[str] = Field(
        default=["image/jpeg", "image/png", "image/webp", "image/tiff"],
        description="Accepted image MIME types",
    )

    # --- Blur Pipeline ---
    BLUR_ENABLED: bool = Field(
        default=True, description="Enable face/plate blurring"
    )
    BLUR_MODE: str = Field(
        default="stub",
        description="Blur mode: 'model' (production) or 'stub' (dev/testing)",
    )

    # --- Detection ---
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.4,
        description="Detections below this confidence go to human review queue",
    )

    # --- Server ---
    HOST: str = Field(default="0.0.0.0", description="Server bind host")
    PORT: int = Field(default=8001, description="Server bind port")
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton settings instance
settings = Settings()
