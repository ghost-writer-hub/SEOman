"""
Dashboard schemas.
"""
from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema


class DashboardStats(BaseSchema):
    """Overall dashboard statistics."""
    
    sites_count: int
    total_audits: int
    total_keywords: int
    total_content_briefs: int
    total_plans: int


class SiteDashboard(BaseSchema):
    """Site-specific dashboard data."""
    
    site_id: UUID
    site_name: str
    latest_audit_score: int | None
    latest_audit_date: datetime | None
    open_issues_by_severity: dict[str, int]
    keyword_opportunities_count: int
    content_briefs_count: int
    content_drafts_count: int
    active_plan_progress: dict | None


class AuditTrend(BaseSchema):
    """Audit score trend data."""
    
    date: datetime
    score: int
    issues_count: int


class KeywordSummary(BaseSchema):
    """Keyword research summary."""
    
    total_keywords: int
    total_clusters: int
    total_search_volume: int
    top_keywords: list[dict]
    top_clusters: list[dict]


class ContentSummary(BaseSchema):
    """Content generation summary."""
    
    total_briefs: int
    total_drafts: int
    drafts_by_status: dict[str, int]
    recent_drafts: list[dict]
