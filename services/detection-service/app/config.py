"""
Detection service configuration.

Controls model paths, detection thresholds, queue names, and
connections for the detection worker.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Detection service configuration."""

    # --- Model Configuration ---
    MODEL_MODE: str = Field(
        default="stub",
        description="Model mode: 'stub' (dev/testing) or 'model' (production)",
    )
    YOLO_MODEL_PATH: str = Field(
        default="models/yolov8n-civic.pt",
        description="Path to YOLOv8 multi-class weights",
    )
    SEG_MODEL_PATH: str = Field(
        default="models/seg-civic.pt",
        description="Path to segmentation model weights",
    )

    # --- Detection Thresholds ---
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.4,
        description="Below this → status='under_review' (human review queue)",
    )
    MIN_DETECTION_THRESHOLD: float = Field(
        default=0.1,
        description="Below this → treat as no detection found",
    )

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/urbanpulse",
        description="PostgreSQL connection string",
    )

    # --- Redis Queue ---
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    INPUT_QUEUE: str = Field(
        default="detection_jobs",
        description="Queue to consume detection jobs from",
    )
    OUTPUT_QUEUE: str = Field(
        default="scoring_jobs",
        description="Queue to publish scoring jobs to",
    )
    DEDUP_QUEUE: str = Field(
        default="dedup_jobs",
        description="Queue to publish dedup jobs to",
    )

    # --- S3 (for downloading images) ---
    S3_ENDPOINT: str = Field(default="http://localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_REGION: str = Field(default="us-east-1")

    # --- Worker ---
    WORKER_POLL_TIMEOUT: int = Field(
        default=5,
        description="BRPOP timeout in seconds (0 = blocking forever)",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
