from pydantic import BaseModel, HttpUrl, Field, constr, ConfigDict
from typing import Optional
from datetime import datetime

class URLRequest(BaseModel):
    """Request model for URL shortening."""
    long_url: HttpUrl = Field(..., description="The URL to be shortened")
    custom_slug: Optional[str] = Field(
        None,
        description="Optional custom slug for the shortened URL. Must be 1-32 characters and contain only letters, numbers, underscores, hyphens, and forward slashes.",
        min_length=1,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_/-]+$"
    )

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "long_url": "https://example.com/very/long/url",
                "custom_slug": "my/custom/slug"
            }
        }
    )

class URLResponse(BaseModel):
    """Response model for shortened URL."""
    short_url: str = Field(..., description="The shortened URL")
    long_url: Optional[str] = Field(None, description="The original long URL")
    clicks: int = Field(default=0, description="Number of times the URL has been accessed")
    created_at: datetime = Field(..., description="When the URL was shortened")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "short_url": "http://localhost:8000/abc123",
                "long_url": "https://example.com/very/long/url",
                "clicks": 0,
                "created_at": "2024-03-20T12:00:00"
            }
        }
    )
