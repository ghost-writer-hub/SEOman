"""
Export Tasks

Background tasks for generating reports and data exports.
"""

import asyncio
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from celery import shared_task
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.site import Site
from app.models.audit import AuditRun, SeoIssue
from app.models.keyword import Keyword, KeywordCluster
from app.models.content import ContentBrief, ContentDraft
from app.integrations.storage import get_storage_client, SEOmanStoragePaths


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(bind=True)
def export_audit_report(
    self,
    audit_id: str,
    site_id: str,
    tenant_id: str,
    format: str = "json",
):
    """Export audit report in specified format."""
    return run_async(_export_audit_report(audit_id, site_id, tenant_id, format))


async def _export_audit_report(
    audit_id: str,
    site_id: str,
    tenant_id: str,
    format: str,
) -> Dict[str, Any]:
    """Generate and store audit report export."""
    async with async_session_maker() as session:
        audit = await session.get(AuditRun, UUID(audit_id))
        site = await session.get(Site, UUID(site_id))
        
        if not audit or not site:
            return {"error": "Audit or site not found"}
        
        # Get issues
        stmt = select(SeoIssue).where(SeoIssue.audit_id == audit.id)
        result = await session.execute(stmt)
        issues = result.scalars().all()
        
        # Build report data
        report = {
            "site": {
                "id": str(site.id),
                "name": site.name,
                "url": site.url,
            },
            "audit": {
                "id": str(audit.id),
                "status": audit.status.value if audit.status else "unknown",
                "score": audit.score,
                "started_at": audit.started_at.isoformat() if audit.started_at else None,
                "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
                "issues_count": audit.issues_count,
                "critical_count": audit.critical_count,
                "high_count": audit.high_count,
                "medium_count": audit.medium_count,
                "low_count": audit.low_count,
            },
            "issues": [
                {
                    "category": issue.category,
                    "severity": issue.severity.value if issue.severity else "low",
                    "title": issue.title,
                    "description": issue.description,
                    "affected_url": issue.affected_url,
                    "recommendation": issue.recommendation,
                }
                for issue in issues
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        # Convert to requested format
        export_id = str(uuid4())
        
        if format == "csv":
            filename = f"audit_report_{audit_id}.csv"
            content = _convert_to_csv(report)
            content_type = "text/csv"
        else:
            filename = f"audit_report_{audit_id}.json"
            content = json.dumps(report, indent=2).encode("utf-8")
            content_type = "application/json"
        
        # Store in object storage
        try:
            storage = get_storage_client()
            export_path = SEOmanStoragePaths.export(
                tenant_id, "audit", export_id, filename
            )
            storage.upload_bytes(export_path, content, content_type=content_type)
            
            # Generate download URL
            download_url = storage.get_presigned_url(
                export_path,
                expires=timedelta(hours=24),
            )
            
            return {
                "export_id": export_id,
                "filename": filename,
                "download_url": download_url,
                "expires_in": "24 hours",
            }
            
        except Exception as e:
            return {"error": str(e)}


def _convert_to_csv(report: Dict[str, Any]) -> bytes:
    """Convert report to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Category", "Severity", "Title", "Description",
        "Affected URL", "Recommendation"
    ])
    
    # Data rows
    for issue in report.get("issues", []):
        writer.writerow([
            issue.get("category", ""),
            issue.get("severity", ""),
            issue.get("title", ""),
            issue.get("description", ""),
            issue.get("affected_url", ""),
            issue.get("recommendation", ""),
        ])
    
    return output.getvalue().encode("utf-8")


@shared_task(bind=True)
def export_keywords(
    self,
    site_id: str,
    tenant_id: str,
    format: str = "csv",
    include_rankings: bool = True,
):
    """Export keywords for a site."""
    return run_async(_export_keywords(site_id, tenant_id, format, include_rankings))


async def _export_keywords(
    site_id: str,
    tenant_id: str,
    format: str,
    include_rankings: bool,
) -> Dict[str, Any]:
    """Generate keyword export."""
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))
        
        if not site:
            return {"error": "Site not found"}
        
        # Get keywords
        stmt = select(Keyword).where(Keyword.site_id == site.id)
        result = await session.execute(stmt)
        keywords = result.scalars().all()
        
        export_id = str(uuid4())
        
        if format == "csv":
            filename = f"keywords_{site_id}.csv"
            content = _keywords_to_csv(keywords, include_rankings)
            content_type = "text/csv"
        else:
            filename = f"keywords_{site_id}.json"
            data = [
                {
                    "keyword": kw.keyword,
                    "search_volume": kw.search_volume,
                    "cpc": kw.cpc,
                    "competition": kw.competition,
                    "difficulty": kw.difficulty,
                    "intent": kw.intent,
                    "current_position": kw.current_position if include_rankings else None,
                    "is_tracked": kw.is_tracked,
                }
                for kw in keywords
            ]
            content = json.dumps(data, indent=2).encode("utf-8")
            content_type = "application/json"
        
        try:
            storage = get_storage_client()
            export_path = SEOmanStoragePaths.export(
                tenant_id, "keywords", export_id, filename
            )
            storage.upload_bytes(export_path, content, content_type=content_type)
            
            download_url = storage.get_presigned_url(
                export_path,
                expires=timedelta(hours=24),
            )
            
            return {
                "export_id": export_id,
                "filename": filename,
                "download_url": download_url,
                "keywords_count": len(keywords),
            }
            
        except Exception as e:
            return {"error": str(e)}


def _keywords_to_csv(keywords: List[Keyword], include_rankings: bool) -> bytes:
    """Convert keywords to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ["Keyword", "Search Volume", "CPC", "Competition", "Difficulty", "Intent"]
    if include_rankings:
        headers.extend(["Current Position", "Is Tracked"])
    
    writer.writerow(headers)
    
    for kw in keywords:
        row = [
            kw.keyword,
            kw.search_volume or "",
            kw.cpc or "",
            kw.competition or "",
            kw.difficulty or "",
            kw.intent or "",
        ]
        if include_rankings:
            row.extend([kw.current_position or "", kw.is_tracked])
        writer.writerow(row)
    
    return output.getvalue().encode("utf-8")


@shared_task(bind=True)
def generate_weekly_reports(self):
    """Generate weekly reports for all tenants."""
    return run_async(_generate_weekly_reports())


async def _generate_weekly_reports():
    """Generate and email weekly reports."""
    async with async_session_maker() as session:
        # Get all sites that had activity this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        stmt = select(Site).where(Site.updated_at >= week_ago)
        result = await session.execute(stmt)
        sites = result.scalars().all()
        
        reports_generated = 0
        
        for site in sites:
            # Get latest audit
            audit_stmt = (
                select(AuditRun)
                .where(AuditRun.site_id == site.id)
                .order_by(AuditRun.created_at.desc())
                .limit(1)
            )
            audit_result = await session.execute(audit_stmt)
            latest_audit = audit_result.scalar_one_or_none()
            
            # Get keyword count
            kw_stmt = select(Keyword).where(Keyword.site_id == site.id)
            kw_result = await session.execute(kw_stmt)
            keywords = kw_result.scalars().all()
            
            report = {
                "site": {
                    "name": site.name,
                    "url": site.url,
                },
                "period": {
                    "start": week_ago.isoformat(),
                    "end": datetime.utcnow().isoformat(),
                },
                "audit": {
                    "score": latest_audit.score if latest_audit else None,
                    "issues": latest_audit.issues_count if latest_audit else None,
                },
                "keywords": {
                    "total": len(keywords),
                    "tracked": sum(1 for kw in keywords if kw.is_tracked),
                },
            }
            
            # Store report
            try:
                storage = get_storage_client()
                report_id = str(uuid4())
                report_path = SEOmanStoragePaths.export(
                    str(site.tenant_id),
                    "weekly",
                    report_id,
                    f"weekly_report_{site.id}.json",
                )
                storage.upload_json(report_path, report)
                reports_generated += 1
            except Exception:
                pass
        
        return {"reports_generated": reports_generated}


@shared_task(bind=True)
def cleanup_old_exports(self):
    """Clean up exports older than 30 days."""
    return run_async(_cleanup_old_exports())


async def _cleanup_old_exports():
    """Remove old export files from storage."""
    try:
        storage = get_storage_client()
        
        # List all exports
        exports = storage.list_objects(prefix="tenants/", recursive=True)
        
        cutoff = datetime.utcnow() - timedelta(days=30)
        deleted = 0
        
        for obj in exports:
            if "/exports/" in obj.key and obj.last_modified < cutoff:
                storage.delete(obj.key)
                deleted += 1
        
        return {"exports_deleted": deleted}
        
    except Exception as e:
        return {"error": str(e)}


@shared_task(bind=True)
def export_site_data(
    self,
    site_id: str,
    tenant_id: str,
    include_audits: bool = True,
    include_keywords: bool = True,
    include_content: bool = True,
):
    """Export all data for a site."""
    return run_async(_export_site_data(
        site_id, tenant_id, include_audits, include_keywords, include_content
    ))


async def _export_site_data(
    site_id: str,
    tenant_id: str,
    include_audits: bool,
    include_keywords: bool,
    include_content: bool,
) -> Dict[str, Any]:
    """Generate complete site data export."""
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))
        
        if not site:
            return {"error": "Site not found"}
        
        export_data = {
            "site": {
                "id": str(site.id),
                "name": site.name,
                "url": site.url,
                "created_at": site.created_at.isoformat() if site.created_at else None,
            },
            "exported_at": datetime.utcnow().isoformat(),
        }
        
        if include_audits:
            audit_stmt = (
                select(AuditRun)
                .where(AuditRun.site_id == site.id)
                .order_by(AuditRun.created_at.desc())
                .limit(10)
            )
            audit_result = await session.execute(audit_stmt)
            audits = audit_result.scalars().all()
            
            export_data["audits"] = [
                {
                    "id": str(a.id),
                    "score": a.score,
                    "status": a.status.value if a.status else None,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in audits
            ]
        
        if include_keywords:
            kw_stmt = select(Keyword).where(Keyword.site_id == site.id)
            kw_result = await session.execute(kw_stmt)
            keywords = kw_result.scalars().all()
            
            export_data["keywords"] = [
                {
                    "keyword": kw.keyword,
                    "search_volume": kw.search_volume,
                    "position": kw.current_position,
                    "is_tracked": kw.is_tracked,
                }
                for kw in keywords
            ]
        
        if include_content:
            brief_stmt = select(ContentBrief).where(ContentBrief.site_id == site.id)
            brief_result = await session.execute(brief_stmt)
            briefs = brief_result.scalars().all()
            
            export_data["content_briefs"] = [
                {
                    "id": str(b.id),
                    "target_keyword": b.target_keyword,
                    "status": b.status.value if b.status else None,
                }
                for b in briefs
            ]
        
        export_id = str(uuid4())
        filename = f"site_export_{site_id}.json"
        
        try:
            storage = get_storage_client()
            export_path = SEOmanStoragePaths.export(
                tenant_id, "full", export_id, filename
            )
            storage.upload_json(export_path, export_data)
            
            download_url = storage.get_presigned_url(
                export_path,
                expires=timedelta(hours=48),
            )
            
            return {
                "export_id": export_id,
                "filename": filename,
                "download_url": download_url,
            }
            
        except Exception as e:
            return {"error": str(e)}
