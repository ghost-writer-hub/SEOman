"""
Usage tracking models for rate limiting and quotas.
"""
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Column, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class UsageType(str, PyEnum):
    """Types of tracked usage."""
    API_CALL = "api_call"
    CRAWL_PAGE = "crawl_page"
    KEYWORD_LOOKUP = "keyword_lookup"
    AUDIT_RUN = "audit_run"
    CONTENT_GENERATION = "content_generation"
    JS_RENDER = "js_render"


class TenantUsage(Base, BaseModel):
    """Monthly usage tracking per tenant."""

    __tablename__ = "tenant_usage"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month = Column(Date, nullable=False, index=True)

    # Usage counters
    api_calls = Column(Integer, default=0)
    pages_crawled = Column(Integer, default=0)
    keywords_researched = Column(Integer, default=0)
    audits_run = Column(Integer, default=0)
    content_generated = Column(Integer, default=0)
    js_renders = Column(Integer, default=0)

    # Breakdown by endpoint (optional detailed tracking)
    endpoint_usage = Column(JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="usage_records")

    __table_args__ = (
        UniqueConstraint("tenant_id", "month", name="uq_tenant_usage_month"),
    )

    def __repr__(self) -> str:
        return f"<TenantUsage tenant={self.tenant_id} month={self.month}>"


class TenantQuota(Base, BaseModel):
    """Quota configuration per tenant (overrides plan defaults)."""

    __tablename__ = "tenant_quotas"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Monthly quotas (None = use plan default)
    monthly_api_calls = Column(Integer, nullable=True)
    monthly_crawl_pages = Column(Integer, nullable=True)
    monthly_keyword_lookups = Column(Integer, nullable=True)
    monthly_audits = Column(Integer, nullable=True)
    monthly_content_generations = Column(Integer, nullable=True)
    monthly_js_renders = Column(Integer, nullable=True)

    # Rate limits (requests per minute)
    rate_limit_per_minute = Column(Integer, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="quota")

    def __repr__(self) -> str:
        return f"<TenantQuota tenant={self.tenant_id}>"


class RateLimitEvent(Base, BaseModel):
    """Log of rate limit events for monitoring."""

    __tablename__ = "rate_limit_events"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    endpoint = Column(String(255), nullable=False)
    limit_type = Column(String(50), nullable=False)  # "rate" or "quota"
    limit_value = Column(Integer, nullable=False)
    current_value = Column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<RateLimitEvent {self.limit_type} on {self.endpoint}>"
