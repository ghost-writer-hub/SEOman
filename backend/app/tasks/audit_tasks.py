"""
Audit Tasks

Background tasks for SEO audit processing.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.audit import AuditRun, SeoIssue, IssueSeverity
from app.models.crawl import JobStatus
from app.models.site import Site
from app.integrations.seoanalyzer import SEOAnalyzerClient
from app.integrations.llm import get_llm_client, analyze_seo_issues
from app.integrations.storage import get_storage_client, SEOmanStoragePaths


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(bind=True, max_retries=3)
def run_audit(self, audit_id: str, site_id: str, tenant_id: str):
    """Run an SEO audit for a site."""
    return run_async(_run_audit(self, audit_id, site_id, tenant_id))


async def _run_audit(task, audit_id: str, site_id: str, tenant_id: str):
    """Async implementation of audit run."""
    async with async_session_maker() as session:
        # Get site and audit
        site = await session.get(Site, UUID(site_id))
        audit = await session.get(AuditRun, UUID(audit_id))
        
        if not site or not audit:
            return {"error": "Site or audit not found"}
        
        # Update status
        audit.status = JobStatus.RUNNING
        audit.started_at = datetime.utcnow()
        await session.commit()
        
        try:
            # Run SEO analysis
            analyzer = SEOAnalyzerClient()
            result = await analyzer.analyze_site(
                url=site.url,
                sitemap=None,
                analyze_headings=True,
                analyze_extra_tags=True,
            )
            
            if not result.get("success"):
                raise Exception(result.get("error", "Analysis failed"))
            
            # Process issues
            issues_data = result.get("issues", [])
            total_issues = 0
            severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }
            
            for issue_data in issues_data:
                severity = _map_severity(issue_data.get("severity", "low"))
                severity_counts[severity.value] += 1
                total_issues += 1
                
                issue = SeoIssue(
                    audit_id=audit.id,
                    category=issue_data.get("category", "general"),
                    severity=severity,
                    title=issue_data.get("title", "Unknown issue"),
                    description=issue_data.get("description"),
                    affected_url=issue_data.get("url"),
                    recommendation=issue_data.get("recommendation"),
                )
                session.add(issue)
            
            # Calculate score
            score = _calculate_audit_score(severity_counts, total_issues)
            
            # Get AI recommendations if LLM available
            recommendations = None
            try:
                llm = get_llm_client()
                if await llm.health_check():
                    ai_result = await analyze_seo_issues(llm, site.url, issues_data)
                    recommendations = ai_result
            except Exception:
                pass  # AI analysis is optional
            
            # Update audit
            audit.status = JobStatus.COMPLETED
            audit.completed_at = datetime.utcnow()
            audit.score = score
            audit.issues_count = total_issues
            audit.critical_count = severity_counts["critical"]
            audit.high_count = severity_counts["high"]
            audit.medium_count = severity_counts["medium"]
            audit.low_count = severity_counts["low"]
            
            if recommendations:
                audit.ai_recommendations = recommendations
            
            await session.commit()
            
            # Store full report in object storage
            try:
                storage = get_storage_client()
                report_path = SEOmanStoragePaths.audit_report(
                    tenant_id, site_id, audit_id
                )
                storage.upload_json(report_path, {
                    "audit_id": audit_id,
                    "site_url": site.url,
                    "score": score,
                    "issues": issues_data,
                    "recommendations": recommendations,
                    "completed_at": datetime.utcnow().isoformat(),
                })
            except Exception:
                pass  # Storage is optional
            
            return {
                "audit_id": audit_id,
                "status": "completed",
                "score": score,
                "issues_count": total_issues,
            }
            
        except Exception as e:
            audit.status = JobStatus.FAILED
            audit.error_message = str(e)
            audit.completed_at = datetime.utcnow()
            await session.commit()
            
            raise task.retry(exc=e, countdown=120)


def _map_severity(severity_str: str) -> IssueSeverity:
    """Map string severity to enum."""
    mapping = {
        "critical": IssueSeverity.CRITICAL,
        "high": IssueSeverity.HIGH,
        "medium": IssueSeverity.MEDIUM,
        "low": IssueSeverity.LOW,
    }
    return mapping.get(severity_str.lower(), IssueSeverity.LOW)


def _calculate_audit_score(severity_counts: Dict[str, int], total_issues: int) -> int:
    """Calculate audit score based on issues found."""
    if total_issues == 0:
        return 100
    
    # Deduct points based on severity
    deductions = (
        severity_counts["critical"] * 15 +
        severity_counts["high"] * 10 +
        severity_counts["medium"] * 5 +
        severity_counts["low"] * 2
    )
    
    score = max(0, 100 - deductions)
    return score


@shared_task(bind=True)
def process_scheduled_audits(self):
    """Process scheduled audits that are due to run."""
    return run_async(_process_scheduled_audits())


async def _process_scheduled_audits():
    """Find and queue scheduled audits."""
    async with async_session_maker() as session:
        # Find sites with scheduled audits due
        now = datetime.utcnow()
        
        stmt = select(Site).where(
            Site.next_audit_at <= now,
            Site.audit_schedule.isnot(None),
        )
        
        result = await session.execute(stmt)
        sites = result.scalars().all()
        
        queued = 0
        for site in sites:
            # Create new audit
            audit = AuditRun(
                site_id=site.id,
                tenant_id=site.tenant_id,
                status=JobStatus.PENDING,
                audit_type="scheduled",
            )
            session.add(audit)
            await session.flush()
            
            # Queue the audit task
            run_audit.delay(
                str(audit.id),
                str(site.id),
                str(site.tenant_id),
            )
            
            # Update next audit time
            site.last_audit_at = now
            site.next_audit_at = _calculate_next_audit(site.audit_schedule)
            
            queued += 1
        
        await session.commit()
        
        return {"scheduled_audits_queued": queued}


def _calculate_next_audit(schedule: str) -> datetime:
    """Calculate next audit time based on schedule."""
    from datetime import timedelta
    
    now = datetime.utcnow()
    
    if schedule == "daily":
        return now + timedelta(days=1)
    elif schedule == "weekly":
        return now + timedelta(weeks=1)
    elif schedule == "monthly":
        return now + timedelta(days=30)
    else:
        return now + timedelta(weeks=1)  # Default weekly


@shared_task(bind=True)
def compare_audits(self, audit_id_1: str, audit_id_2: str):
    """Compare two audits and generate diff report."""
    return run_async(_compare_audits(audit_id_1, audit_id_2))


async def _compare_audits(audit_id_1: str, audit_id_2: str) -> Dict[str, Any]:
    """Generate comparison between two audits."""
    async with async_session_maker() as session:
        audit1 = await session.get(AuditRun, UUID(audit_id_1))
        audit2 = await session.get(AuditRun, UUID(audit_id_2))
        
        if not audit1 or not audit2:
            return {"error": "One or both audits not found"}
        
        # Get issues for both audits
        stmt1 = select(SeoIssue).where(SeoIssue.audit_id == audit1.id)
        stmt2 = select(SeoIssue).where(SeoIssue.audit_id == audit2.id)
        
        result1 = await session.execute(stmt1)
        result2 = await session.execute(stmt2)
        
        issues1 = {(i.category, i.title): i for i in result1.scalars().all()}
        issues2 = {(i.category, i.title): i for i in result2.scalars().all()}
        
        # Find differences
        keys1 = set(issues1.keys())
        keys2 = set(issues2.keys())
        
        new_issues = keys2 - keys1
        fixed_issues = keys1 - keys2
        persistent_issues = keys1 & keys2
        
        return {
            "audit_1": {
                "id": audit_id_1,
                "score": audit1.score,
                "issues_count": audit1.issues_count,
            },
            "audit_2": {
                "id": audit_id_2,
                "score": audit2.score,
                "issues_count": audit2.issues_count,
            },
            "score_change": (audit2.score or 0) - (audit1.score or 0),
            "new_issues": len(new_issues),
            "fixed_issues": len(fixed_issues),
            "persistent_issues": len(persistent_issues),
        }
