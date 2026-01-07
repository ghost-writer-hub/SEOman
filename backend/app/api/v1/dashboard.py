"""
Dashboard endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.audit import AuditRun, SeoIssue, IssueStatus
from app.models.crawl import JobStatus
from app.models.keyword import Keyword, KeywordCluster
from app.models.content import ContentBrief, ContentDraft
from app.models.plan import SeoPlan
from app.schemas.dashboard import DashboardStats, SiteDashboard
from app.services.site_service import SiteService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get overall dashboard statistics for the tenant."""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User is not in a tenant")
    
    from app.models.site import Site
    
    # Count sites
    sites_result = await db.execute(
        select(func.count(Site.id)).where(Site.tenant_id == current_user.tenant_id)
    )
    sites_count = sites_result.scalar()
    
    # Get site IDs for further queries
    sites_query = await db.execute(
        select(Site.id).where(Site.tenant_id == current_user.tenant_id)
    )
    site_ids = [row[0] for row in sites_query.all()]
    
    if not site_ids:
        return DashboardStats(
            sites_count=0,
            total_audits=0,
            total_keywords=0,
            total_content_briefs=0,
            total_plans=0,
        )
    
    # Count audits
    audits_result = await db.execute(
        select(func.count(AuditRun.id)).where(AuditRun.site_id.in_(site_ids))
    )
    total_audits = audits_result.scalar()
    
    # Count keywords
    keywords_result = await db.execute(
        select(func.count(Keyword.id)).where(Keyword.site_id.in_(site_ids))
    )
    total_keywords = keywords_result.scalar()
    
    # Count briefs
    briefs_result = await db.execute(
        select(func.count(ContentBrief.id)).where(ContentBrief.site_id.in_(site_ids))
    )
    total_briefs = briefs_result.scalar()
    
    # Count plans
    plans_result = await db.execute(
        select(func.count(SeoPlan.id)).where(SeoPlan.site_id.in_(site_ids))
    )
    total_plans = plans_result.scalar()
    
    return DashboardStats(
        sites_count=sites_count,
        total_audits=total_audits,
        total_keywords=total_keywords,
        total_content_briefs=total_briefs,
        total_plans=total_plans,
    )


@router.get("/sites/{site_id}", response_model=SiteDashboard)
async def get_site_dashboard(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get dashboard data for a specific site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    audit_service = AuditService(db)
    latest_audit = await audit_service.get_latest_audit(site_id)
    
    # Count open issues by severity
    open_issues_result = await db.execute(
        select(SeoIssue.severity, func.count(SeoIssue.id))
        .where(
            SeoIssue.site_id == site_id,
            SeoIssue.status == IssueStatus.OPEN,
        )
        .group_by(SeoIssue.severity)
    )
    open_issues_by_severity = {
        str(row[0].value): row[1] for row in open_issues_result.all()
    }
    
    # Count keywords
    keywords_result = await db.execute(
        select(func.count(Keyword.id)).where(Keyword.site_id == site_id)
    )
    keywords_count = keywords_result.scalar()
    
    # Count briefs
    briefs_result = await db.execute(
        select(func.count(ContentBrief.id)).where(ContentBrief.site_id == site_id)
    )
    briefs_count = briefs_result.scalar()
    
    # Count drafts
    drafts_result = await db.execute(
        select(func.count(ContentDraft.id)).where(ContentDraft.site_id == site_id)
    )
    drafts_count = drafts_result.scalar()
    
    return SiteDashboard(
        site_id=site_id,
        site_name=site.name,
        latest_audit_score=latest_audit.score if latest_audit else None,
        latest_audit_date=latest_audit.completed_at if latest_audit else None,
        open_issues_by_severity=open_issues_by_severity,
        keyword_opportunities_count=keywords_count,
        content_briefs_count=briefs_count,
        content_drafts_count=drafts_count,
        active_plan_progress=None,  # TODO: Implement plan progress
    )
