"""
Audit models for SEO analysis results.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel
from app.models.crawl import JobStatus


class IssueSeverity(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, PyEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class AuditRun(Base, BaseModel):
    """Audit run tracking and results."""
    
    __tablename__ = "audit_runs"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crawl_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id"),
        nullable=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    audit_type = Column(String(50), default="quick")
    status = Column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
    )
    score = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    findings_overview = Column(JSONB, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="audit_runs")
    crawl_job = relationship("CrawlJob", back_populates="audit_runs")
    issues = relationship("SeoIssue", back_populates="audit_run", cascade="all, delete-orphan")
    seo_plans = relationship("SeoPlan", back_populates="generated_from_audit")
    
    def __repr__(self) -> str:
        return f"<AuditRun {self.id} ({self.status.value})>"


class SeoIssue(Base, BaseModel):
    """Individual SEO issue found during audit."""
    
    __tablename__ = "seo_issues"
    
    audit_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    severity = Column(
        Enum(IssueSeverity),
        nullable=False,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    affected_urls = Column(JSONB, default=list)
    status = Column(
        Enum(IssueStatus),
        default=IssueStatus.OPEN,
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    audit_run = relationship("AuditRun", back_populates="issues")
    
    def __repr__(self) -> str:
        return f"<SeoIssue {self.title[:30]}... ({self.severity.value})>"
