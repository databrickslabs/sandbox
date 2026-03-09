"""
Common schemas shared across the API.
"""

from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="API status", example="healthy")
    version: str = Field(..., description="API version", example="0.1.0")


class ReadyResponse(BaseModel):
    """Readiness check response."""

    ready: bool = Field(..., description="Whether the API is ready to accept requests")
    database: str = Field(..., description="Database connection status")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Number of items per page", ge=1)
    total_pages: int = Field(..., description="Total number of pages", ge=1)

    class Config:
        from_attributes = True
