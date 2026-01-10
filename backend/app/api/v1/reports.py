"""
Report download endpoints for PDF generation.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, get_db
from app.models.audit import AuditRun, SeoIssue, SEOAuditCheck
from app.models.crawl import JobStatus
from app.models.site import Site
from app.schemas.report import PDFOptions, ReportGenerateRequest
from app.services.pdf_generator import PDFGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])


async def get_audit_with_site(
    db: AsyncSession,
    audit_id: UUID,
    tenant_id: UUID,
) -> AuditRun | None:
    """Get an audit run with its associated site."""
    result = await db.execute(
        select(AuditRun)
        .options(selectinload(AuditRun.site))
        .join(Site)
        .where(
            AuditRun.id == audit_id,
            Site.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def get_audit_issues(
    db: AsyncSession,
    audit_id: UUID,
) -> list[SeoIssue]:
    """Get all issues for an audit."""
    result = await db.execute(
        select(SeoIssue)
        .where(SeoIssue.audit_run_id == audit_id)
        .order_by(
            SeoIssue.severity.desc(),
            SeoIssue.title,
        )
    )
    return list(result.scalars().all())


async def get_audit_checks(
    db: AsyncSession,
    audit_id: UUID,
) -> list[SEOAuditCheck]:
    """Get all audit checks (failed ones) for an audit."""
    result = await db.execute(
        select(SEOAuditCheck)
        .where(
            SEOAuditCheck.audit_run_id == audit_id,
            SEOAuditCheck.passed == 0,  # Only failed checks
        )
        .order_by(SEOAuditCheck.check_id)
    )
    return list(result.scalars().all())


@router.get("/audits/{audit_id}/pdf")
async def download_audit_pdf(
    audit_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_code_examples: bool = Query(default=True, description="Include code fix examples"),
    max_urls_per_issue: int = Query(default=10, ge=1, le=50, description="Max URLs per issue"),
    logo_url: str | None = Query(default=None, description="Custom logo URL"),
    brand_color: str = Query(default="#2563eb", pattern=r"^#[0-9a-fA-F]{6}$", description="Brand color"),
):
    """
    Download audit report as PDF.

    Generates a professional PDF report from the audit data including:
    - Overall score with visual badge
    - Executive summary with severity breakdown
    - Detailed issues organized by priority
    - Code fix examples (optional)
    - List of affected URLs per issue

    Returns the PDF as a downloadable file.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Get audit with site
    audit_run = await get_audit_with_site(db, audit_id, current_user.tenant_id)
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )

    if audit_run.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audit is not completed (status: {audit_run.status.value})",
        )

    # Get audit checks (failed ones become issues)
    checks = await get_audit_checks(db, audit_id)

    # Convert checks to issue format for PDF
    issues = []
    for check in checks:
        issues.append({
            "title": check.check_name,
            "category": check.category,
            "severity": check.severity or "medium",
            "description": check.recommendation,
            "affected_urls": check.affected_urls or [],
            "details": check.details or {},
        })

    # Also get SeoIssue records if any
    seo_issues = await get_audit_issues(db, audit_id)
    for issue in seo_issues:
        issues.append({
            "title": issue.title,
            "category": issue.category,
            "severity": issue.severity.value if issue.severity else "medium",
            "description": issue.description,
            "recommendation": issue.suggested_fix,
            "affected_urls": issue.affected_urls or [],
            "details": {},
        })

    # Deduplicate by title
    seen_titles = set()
    unique_issues = []
    for issue in issues:
        if issue["title"] not in seen_titles:
            seen_titles.add(issue["title"])
            unique_issues.append(issue)

    # Build audit data
    audit_data = {
        "generated_at": audit_run.completed_at.strftime("%Y-%m-%d %H:%M UTC") if audit_run.completed_at else "",
        "checks_run": 100,
        "pages_crawled": audit_run.findings_overview.get("pages_crawled", 0) if audit_run.findings_overview else 0,
    }

    # Generate PDF
    pdf_generator = PDFGenerator()
    try:
        pdf_bytes = await pdf_generator.generate_audit_pdf(
            audit_data=audit_data,
            issues=unique_issues,
            site_url=audit_run.site.primary_domain,
            score=audit_run.score or 0,
            logo_url=logo_url,
            brand_color=brand_color,
            include_code_examples=include_code_examples,
            max_urls_per_issue=max_urls_per_issue,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    # Generate filename
    site_domain = audit_run.site.primary_domain.replace("https://", "").replace("http://", "").replace("/", "_")
    date_str = audit_run.completed_at.strftime("%Y%m%d") if audit_run.completed_at else "report"
    filename = f"seo-audit-{site_domain}-{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/sites/{site_id}/audits/latest/pdf")
async def download_latest_audit_pdf(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_code_examples: bool = Query(default=True),
    max_urls_per_issue: int = Query(default=10, ge=1, le=50),
    logo_url: str | None = Query(default=None),
    brand_color: str = Query(default="#2563eb", pattern=r"^#[0-9a-fA-F]{6}$"),
):
    """
    Download the latest completed audit as PDF.

    Convenience endpoint that finds the most recent completed audit
    for the specified site and generates a PDF report.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Get site to verify ownership
    site_result = await db.execute(
        select(Site).where(
            Site.id == site_id,
            Site.tenant_id == current_user.tenant_id,
        )
    )
    site = site_result.scalar_one_or_none()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Get latest completed audit
    audit_result = await db.execute(
        select(AuditRun)
        .where(
            AuditRun.site_id == site_id,
            AuditRun.status == JobStatus.COMPLETED,
        )
        .order_by(AuditRun.completed_at.desc())
        .limit(1)
    )
    audit_run = audit_result.scalar_one_or_none()

    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed audits found for this site",
        )

    # Redirect to the specific audit PDF endpoint
    from fastapi import Request
    from fastapi.responses import RedirectResponse

    # Instead of redirect, just call the same logic
    return await download_audit_pdf(
        audit_id=audit_run.id,
        current_user=current_user,
        db=db,
        include_code_examples=include_code_examples,
        max_urls_per_issue=max_urls_per_issue,
        logo_url=logo_url,
        brand_color=brand_color,
    )
