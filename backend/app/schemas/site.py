"""
Site schemas.
"""
from uuid import UUID

from pydantic import Field, HttpUrl

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class SiteCreate(BaseSchema):
    """Create site request."""
    
    name: str = Field(min_length=2, max_length=255)
    primary_domain: str = Field(min_length=4, max_length=255)
    additional_domains: list[str] = []
    default_language: str = "en"
    target_countries: list[str] = ["US"]
    cms_type: str | None = None
    brand_tone: dict = {}
    enabled_features: list[str] = ["audit", "keywords", "content"]


class SiteUpdate(BaseSchema):
    """Update site request."""
    
    name: str | None = None
    primary_domain: str | None = None
    additional_domains: list[str] | None = None
    default_language: str | None = None
    target_countries: list[str] | None = None
    cms_type: str | None = None
    brand_tone: dict | None = None
    enabled_features: list[str] | None = None


class SiteResponse(IDSchema, TimestampSchema):
    """Site response."""
    
    tenant_id: UUID
    name: str
    primary_domain: str
    additional_domains: list[str]
    default_language: str
    target_countries: list[str]
    cms_type: str | None
    brand_tone: dict
    enabled_features: list[str]


class SiteWithStats(SiteResponse):
    """Site response with statistics."""
    
    last_audit_score: int | None = None
    open_issues_count: int = 0
    keywords_count: int = 0
    content_briefs_count: int = 0
