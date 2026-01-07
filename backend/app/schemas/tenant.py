"""
Tenant schemas.
"""
from uuid import UUID

from pydantic import Field

from app.models.tenant import TenantStatus
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class TenantCreate(BaseSchema):
    """Create tenant request."""
    
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str = "free"


class TenantUpdate(BaseSchema):
    """Update tenant request."""
    
    name: str | None = None
    status: TenantStatus | None = None
    plan: str | None = None
    settings: dict | None = None


class TenantResponse(IDSchema, TimestampSchema):
    """Tenant response."""
    
    name: str
    slug: str
    status: TenantStatus
    plan: str
    settings: dict = {}
