"""
SEO Plan schemas.
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.plan import TaskStatus, TaskCategory
from app.models.audit import IssueSeverity
from app.schemas.common import BaseSchema, IDSchema


class PlanGenerateRequest(BaseSchema):
    """Generate SEO plan request."""
    
    timeframe_months: int = Field(default=6, ge=1, le=12)
    goals: list[str] = []
    name: str | None = None


class SeoPlanResponse(IDSchema):
    """SEO plan response."""
    
    site_id: UUID
    name: str
    timeframe_months: int
    goals: list[str]
    timeline_summary: dict
    generated_from_audit_id: UUID | None
    created_at: datetime
    updated_at: datetime
    tasks_count: int = 0
    completed_tasks_count: int = 0


class SeoTaskResponse(IDSchema):
    """SEO task response."""
    
    seo_plan_id: UUID
    site_id: UUID
    title: str
    description: str | None
    category: TaskCategory
    impact: IssueSeverity
    effort: IssueSeverity
    assignee_type: str | None
    status: TaskStatus
    due_month: int | None
    related_issue_ids: list[str]
    related_cluster_ids: list[str]
    created_at: datetime
    updated_at: datetime


class SeoTaskUpdate(BaseSchema):
    """Update SEO task request."""
    
    status: TaskStatus | None = None
    title: str | None = None
    description: str | None = None
    assignee_type: str | None = None
    due_month: int | None = None


class SeoPlanDetail(SeoPlanResponse):
    """Detailed SEO plan with tasks."""
    
    tasks: list[SeoTaskResponse]
    tasks_by_category: dict[str, int] = {}
    tasks_by_status: dict[str, int] = {}
