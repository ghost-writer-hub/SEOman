"""
Crawl schemas.
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.crawl import JobStatus
from app.schemas.common import BaseSchema, IDSchema


class CrawlConfig(BaseSchema):
    """Crawl configuration."""
    
    max_depth: int = Field(default=3, ge=1, le=10)
    max_pages: int = Field(default=1000, ge=1, le=50000)
    allowed_domains: list[str] = []
    user_agent: str = "SEOman Bot/1.0"
    crawl_delay_ms: int = Field(default=100, ge=0, le=5000)


class CrawlJobCreate(BaseSchema):
    """Create crawl job request."""
    
    config: CrawlConfig = CrawlConfig()


class CrawlJobResponse(IDSchema):
    """Crawl job response."""
    
    site_id: UUID
    status: JobStatus
    config: dict
    pages_crawled: int
    errors_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class CrawlPageResponse(IDSchema):
    """Crawl page response."""
    
    url: str
    status_code: int | None
    content_type: str | None
    title: str | None
    meta_description: str | None
    h1: str | None
    word_count: int | None
    noindex: bool
    nofollow: bool
    created_at: datetime


class CrawlPageDetail(CrawlPageResponse):
    """Detailed crawl page response."""
    
    canonical_url: str | None
    meta_robots: str | None
    h2: list[str]
    h3: list[str]
    internal_links: list[dict]
    external_links: list[dict]
