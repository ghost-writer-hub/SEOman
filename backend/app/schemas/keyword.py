"""
Keyword schemas.
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, IDSchema


class KeywordDiscoverRequest(BaseSchema):
    """Keyword discovery request."""
    
    country: str = "US"
    language: str = "en"
    max_keywords: int = Field(default=100, ge=1, le=1000)


class KeywordExpandRequest(BaseSchema):
    """Keyword expansion request."""
    
    seed_keywords: list[str] = Field(min_length=1, max_length=10)
    country: str = "US"
    language: str = "en"
    max_keywords: int = Field(default=100, ge=1, le=1000)


class KeywordResponse(IDSchema):
    """Keyword response."""
    
    site_id: UUID
    text: str
    language: str
    country: str
    search_volume: int | None
    cpc: Decimal | None
    competition: Decimal | None
    difficulty: int | None
    intent: str | None
    trend: list[dict]
    created_at: datetime


class KeywordClusterResponse(IDSchema):
    """Keyword cluster response."""
    
    site_id: UUID
    label: str
    description: str | None
    language: str
    country: str
    mapped_url: str | None
    is_new_page_recommended: bool
    keywords_count: int = 0
    total_search_volume: int = 0
    created_at: datetime


class KeywordClusterDetail(KeywordClusterResponse):
    """Detailed keyword cluster with keywords."""
    
    keywords: list[KeywordResponse]
    primary_keyword: KeywordResponse | None = None


class KeywordJobResponse(BaseSchema):
    """Keyword job status response."""
    
    job_id: UUID
    status: str
    keywords_found: int = 0
    message: str | None = None
