"""
Audit schemas.
"""
from datetime import datetime
from uuid import UUID

from app.models.crawl import JobStatus
from app.models.audit import IssueSeverity, IssueStatus
from app.schemas.common import BaseSchema, IDSchema


class AuditCreate(BaseSchema):
    """Create audit request."""
    
    audit_type: str = "quick"  # "quick" or "full"
    crawl_job_id: UUID | None = None


class AuditRunResponse(IDSchema):
    """Audit run response."""
    
    site_id: UUID
    crawl_job_id: UUID | None
    audit_type: str
    status: JobStatus
    score: int | None
    summary: str | None
    findings_overview: dict
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class SeoIssueResponse(IDSchema):
    """SEO issue response."""
    
    type: str
    category: str
    severity: IssueSeverity
    title: str
    description: str | None
    suggested_fix: str | None
    affected_urls: list[str]
    status: IssueStatus
    created_at: datetime


class SeoIssueUpdate(BaseSchema):
    """Update SEO issue request."""
    
    status: IssueStatus | None = None


class AuditDetailResponse(BaseSchema):
    """Detailed audit response with issues."""
    
    audit_run: AuditRunResponse
    issues: list[SeoIssueResponse]
    issues_by_severity: dict[str, int] = {}
    issues_by_category: dict[str, int] = {}


class AuditSummary(BaseSchema):
    """Audit summary for dashboard."""
    
    total_audits: int
    latest_score: int | None
    score_trend: list[dict]
    open_issues_count: int
    resolved_issues_count: int
