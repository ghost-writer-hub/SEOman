"""
Common Pydantic schemas used across the API.
"""
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class IDSchema(BaseSchema):
    """Schema with UUID ID."""
    
    id: UUID


class TimestampSchema(BaseSchema):
    """Schema with timestamps."""
    
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated response wrapper."""
    
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int
    
    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
        )


class MessageResponse(BaseSchema):
    """Simple message response."""
    
    message: str
    success: bool = True


class ErrorResponse(BaseSchema):
    """Error response."""
    
    detail: str
    code: str | None = None
