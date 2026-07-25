"""
Pydantic models for request/response schemas.

These models define the API contract for the ingestion service.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ComplaintMetadata(BaseModel):
    """Optional metadata sent alongside the image upload."""

    lat: Optional[float] = Field(None, ge=-90, le=90, description="GPS latitude")
    lng: Optional[float] = Field(None, ge=-180, le=180, description="GPS longitude")
    timestamp: Optional[datetime] = Field(
        None, description="Capture timestamp (ISO 8601)"
    )
    source: str = Field(
        default="mobile_app",
        description="Submission source: mobile_app, cctv, or drone",
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {"mobile_app", "cctv", "drone"}
        if v not in allowed:
            raise ValueError(f"source must be one of {allowed}, got '{v}'")
        return v


class ComplaintResponse(BaseModel):
    """Response returned after successful complaint submission."""

    id: UUID
    status: str = "pending"
    image_url: str
    created_at: datetime
    message: str = "Complaint submitted successfully. Detection in progress."


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: str = "VALIDATION_ERROR"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str = "ingestion-api"
    version: str = "1.0.0"


class DetailedComplaintResponse(BaseModel):
    """Detailed representation of a complaint for read queries."""

    id: UUID
    image_url: str
    blurred_image_url: Optional[str] = None
    lat: float
    lng: float
    issue_class: str
    confidence: float
    severity_score: Optional[float] = None
    priority_score: Optional[float] = None
    status: str
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    sla_deadline: Optional[datetime] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

