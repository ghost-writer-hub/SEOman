"""
Audit service for SEO analysis.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditRun, SeoIssue, IssueSeverity, IssueStatus
from app.models.crawl import JobStatus
from app.schemas.audit import AuditCreate


class AuditService:
    """Service for audit operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, audit_id: UUID, site_id: UUID | None = None) -> AuditRun | None:
        """Get audit by ID."""
        query = select(AuditRun).where(AuditRun.id == audit_id)
        if site_id:
            query = query.where(AuditRun.site_id == site_id)
        query = query.options(selectinload(AuditRun.issues))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_audits(
        self,
        site_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: JobStatus | None = None,
    ) -> tuple[list[AuditRun], int]:
        """List audits for a site with pagination."""
        query = select(AuditRun).where(AuditRun.site_id == site_id)
        count_query = select(func.count(AuditRun.id)).where(AuditRun.site_id == site_id)
        
        if status:
            query = query.where(AuditRun.status == status)
            count_query = count_query.where(AuditRun.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(AuditRun.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        audits = result.scalars().all()
        
        return list(audits), total
    
    async def create(
        self,
        site_id: UUID,
        data: AuditCreate,
        user_id: UUID | None = None,
    ) -> AuditRun:
        """Create a new audit run."""
        audit = AuditRun(
            site_id=site_id,
            audit_type=data.audit_type,
            crawl_job_id=data.crawl_job_id,
            created_by_user_id=user_id,
            status=JobStatus.PENDING,
        )
        self.db.add(audit)
        await self.db.flush()
        await self.db.refresh(audit)
        return audit
    
    async def update_status(
        self,
        audit_id: UUID,
        status: JobStatus,
        error_message: str | None = None,
    ) -> AuditRun | None:
        """Update audit status."""
        audit = await self.get_by_id(audit_id)
        if not audit:
            return None
        
        audit.status = status
        if status == JobStatus.RUNNING and not audit.started_at:
            audit.started_at = datetime.utcnow()
        if status in (JobStatus.COMPLETED, JobStatus.FAILED):
            audit.completed_at = datetime.utcnow()
        if error_message:
            audit.error_message = error_message
        
        await self.db.flush()
        await self.db.refresh(audit)
        return audit
    
    async def save_results(
        self,
        audit_id: UUID,
        score: int,
        summary: str,
        findings_overview: dict,
        issues: list[dict],
    ) -> AuditRun | None:
        """Save audit results and issues."""
        audit = await self.get_by_id(audit_id)
        if not audit:
            return None
        
        audit.score = score
        audit.summary = summary
        audit.findings_overview = findings_overview
        audit.status = JobStatus.COMPLETED
        audit.completed_at = datetime.utcnow()
        
        # Create issues
        for issue_data in issues:
            issue = SeoIssue(
                audit_run_id=audit_id,
                site_id=audit.site_id,
                type=issue_data["type"],
                category=issue_data["category"],
                severity=IssueSeverity(issue_data["severity"]),
                title=issue_data["title"],
                description=issue_data.get("description"),
                suggested_fix=issue_data.get("suggested_fix"),
                affected_urls=issue_data.get("affected_urls", []),
            )
            self.db.add(issue)
        
        await self.db.flush()
        await self.db.refresh(audit)
        return audit
    
    async def get_issues(
        self,
        audit_id: UUID,
        severity: IssueSeverity | None = None,
        status: IssueStatus | None = None,
    ) -> list[SeoIssue]:
        """Get issues for an audit."""
        query = select(SeoIssue).where(SeoIssue.audit_run_id == audit_id)
        
        if severity:
            query = query.where(SeoIssue.severity == severity)
        if status:
            query = query.where(SeoIssue.status == status)
        
        query = query.order_by(SeoIssue.severity.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_issue_status(
        self,
        issue_id: UUID,
        status: IssueStatus,
    ) -> SeoIssue | None:
        """Update issue status."""
        result = await self.db.execute(
            select(SeoIssue).where(SeoIssue.id == issue_id)
        )
        issue = result.scalar_one_or_none()
        if not issue:
            return None
        
        issue.status = status
        if status == IssueStatus.RESOLVED:
            issue.resolved_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(issue)
        return issue
    
    async def get_latest_audit(self, site_id: UUID) -> AuditRun | None:
        """Get the latest completed audit for a site."""
        result = await self.db.execute(
            select(AuditRun)
            .where(
                AuditRun.site_id == site_id,
                AuditRun.status == JobStatus.COMPLETED,
            )
            .order_by(AuditRun.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
