"""
Crawl models for website crawling data.
"""
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class JobStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CrawlJob(Base, BaseModel):
    """Crawl job tracking."""
    
    __tablename__ = "crawl_jobs"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
    )
    config = Column(JSONB, default=dict)
    pages_crawled = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="crawl_jobs")
    pages = relationship("CrawlPage", back_populates="crawl_job", cascade="all, delete-orphan")
    audit_runs = relationship("AuditRun", back_populates="crawl_job")
    
    def __repr__(self) -> str:
        return f"<CrawlJob {self.id} ({self.status.value})>"


class CrawlPage(Base, BaseModel):
    """Crawled page data."""
    
    __tablename__ = "crawl_pages"
    
    crawl_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(Text, nullable=False)
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    canonical_url = Column(Text, nullable=True)
    meta_robots = Column(String(100), nullable=True)
    title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    h1 = Column(Text, nullable=True)
    h2 = Column(JSONB, default=list)
    h3 = Column(JSONB, default=list)
    word_count = Column(Integer, nullable=True)
    internal_links = Column(JSONB, default=list)
    external_links = Column(JSONB, default=list)
    noindex = Column(Boolean, default=False)
    nofollow = Column(Boolean, default=False)
    
    # Relationships
    crawl_job = relationship("CrawlJob", back_populates="pages")
    
    def __repr__(self) -> str:
        return f"<CrawlPage {self.url[:50]}... ({self.status_code})>"
