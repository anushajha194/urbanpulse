"""
Configuration settings for the repair verification service.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Verification service config."""

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/urbanpulse",
        description="PostgreSQL connection string",
    )

    # --- S3 Configuration (for downloading before images and saving after images) ---
    S3_ENDPOINT: str = Field(default="http://localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_REGION: str = Field(default="us-east-1")
    S3_BUCKET: str = Field(default="urbanpulse-images")

    # --- Verification Parameters ---
    MAX_VERIFICATION_DISTANCE_METERS: float = Field(
        default=50.0,
        description="Maximum distance allowed between before and after coordinates in meters",
    )
    MIN_VISUAL_SIMILARITY: float = Field(
        default=0.10,
        description="Minimum structural similarity to confirm it is the same location context",
    )
    MAX_VISUAL_SIMILARITY: float = Field(
        default=0.98,
        description="Maximum similarity - values higher represent duplicate uploads (fraud)",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
