"""
Site model for monitored websites.
"""
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class Site(Base, BaseModel):
    """Site model representing a monitored website."""
    
    __tablename__ = "sites"
    
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    primary_domain = Column(String(255), nullable=False, index=True)
    additional_domains = Column(JSONB, default=list)
    default_language = Column(String(10), default="en")
    target_countries = Column(JSONB, default=lambda: ["US"])
    cms_type = Column(String(100), nullable=True)
    brand_tone = Column(JSONB, default=dict)
    enabled_features = Column(JSONB, default=lambda: ["audit", "keywords", "content"])
    
    # Relationships
    tenant = relationship("Tenant", back_populates="sites")
    crawl_jobs = relationship("CrawlJob", back_populates="site", cascade="all, delete-orphan")
    audit_runs = relationship("AuditRun", back_populates="site", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="site", cascade="all, delete-orphan")
    keyword_clusters = relationship("KeywordCluster", back_populates="site", cascade="all, delete-orphan")
    seo_plans = relationship("SeoPlan", back_populates="site", cascade="all, delete-orphan")
    content_briefs = relationship("ContentBrief", back_populates="site", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Site {self.name} ({self.primary_domain})>"
