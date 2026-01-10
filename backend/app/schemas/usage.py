"""
Usage and quota schemas.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class UsageItemResponse(BaseSchema):
    """Usage for a single metric."""

    used: int = Field(..., description="Amount used this period")
    limit: int = Field(..., description="Maximum allowed (0 = unlimited)")
    remaining: Optional[int] = Field(
        None, description="Remaining quota (null if unlimited)"
    )


class UsageSummaryResponse(BaseSchema):
    """Current usage summary for a tenant."""

    period: str = Field(..., description="Current billing period (YYYY-MM)")
    usage: dict[str, UsageItemResponse]
    rate_limit: dict[str, int]


class UsageHistoryItemResponse(BaseSchema):
    """Usage for a single month."""

    month: str = Field(..., description="Month (YYYY-MM)")
    api_calls: int = 0
    pages_crawled: int = 0
    keywords_researched: int = 0
    audits_run: int = 0
    content_generated: int = 0
    js_renders: int = 0


class QuotaLimitsResponse(BaseSchema):
    """Quota limits for a plan."""

    plan: str
    api_calls: int = Field(..., description="Monthly API call limit (0 = unlimited)")
    crawl_pages: int = Field(..., description="Monthly crawl page limit")
    keyword_lookups: int = Field(..., description="Monthly keyword lookup limit")
    audits: int = Field(..., description="Monthly audit limit")
    content_generations: int = Field(..., description="Monthly content generation limit")
    js_renders: int = Field(..., description="Monthly JS render limit")
    rate_limit_per_minute: int = Field(..., description="API requests per minute")


class TenantQuotaUpdate(BaseSchema):
    """Request to update custom quota overrides (admin only)."""

    monthly_api_calls: Optional[int] = None
    monthly_crawl_pages: Optional[int] = None
    monthly_keyword_lookups: Optional[int] = None
    monthly_audits: Optional[int] = None
    monthly_content_generations: Optional[int] = None
    monthly_js_renders: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None


class RateLimitStatusResponse(BaseSchema):
    """Current rate limit status."""

    limit: int = Field(..., description="Requests per minute limit")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset_at: int = Field(..., description="Unix timestamp when limit resets")
