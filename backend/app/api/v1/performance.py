"""
Performance analysis endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.performance import (
    AnalyzeRequest,
    AnalyzeResponse,
    OpportunitySummary,
    PerformanceHistory,
    PerformanceHistoryPoint,
    PerformanceSnapshotDetail,
    PerformanceSnapshotResponse,
    PerformanceSummary,
)
from app.services.performance_service import PerformanceService
from app.services.site_service import SiteService

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/sites/{site_id}/snapshots", response_model=PaginatedResponse[PerformanceSnapshotResponse])
async def list_performance_snapshots(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    template_type: str | None = None,
    strategy: str | None = None,
):
    """List performance snapshots for a site."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Verify site belongs to tenant
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    service = PerformanceService(db)
    snapshots, total = await service.list_snapshots(
        site_id=site_id,
        template_type=template_type,
        strategy=strategy,
        page=page,
        per_page=per_page,
    )

    return PaginatedResponse.create(
        items=[PerformanceSnapshotResponse.model_validate(s) for s in snapshots],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/sites/{site_id}/summary", response_model=PerformanceSummary)
async def get_performance_summary(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get aggregated performance summary for a site."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Verify site belongs to tenant
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    service = PerformanceService(db)
    summary = await service.get_site_summary(site_id)

    return PerformanceSummary.model_validate(summary)


@router.get("/sites/{site_id}/history", response_model=PerformanceHistory)
async def get_performance_history(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    url: str = Query(..., description="URL to get history for"),
    strategy: str = Query(default="mobile", description="Strategy: mobile or desktop"),
    days: int = Query(default=30, ge=1, le=90, description="Number of days of history"),
):
    """Get performance history for a specific URL."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Verify site belongs to tenant
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    service = PerformanceService(db)
    snapshots = await service.get_performance_history(
        site_id=site_id,
        url=url,
        strategy=strategy,
        days=days,
    )

    history = [
        PerformanceHistoryPoint(
            checked_at=s.checked_at,
            performance_score=s.performance_score,
            lcp_ms=s.lcp_ms,
            cls=s.cls,
            fcp_ms=s.fcp_ms,
            cwv_status=s.cwv_status,
        )
        for s in snapshots
    ]

    return PerformanceHistory(url=url, strategy=strategy, history=history)


@router.get("/sites/{site_id}/opportunities", response_model=list[OpportunitySummary])
async def get_optimization_opportunities(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get aggregated optimization opportunities across all pages."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Verify site belongs to tenant
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    service = PerformanceService(db)
    opportunities = await service.get_opportunities_summary(site_id)

    return [OpportunitySummary.model_validate(o) for o in opportunities]


@router.get("/sites/{site_id}/snapshots/{snapshot_id}", response_model=PerformanceSnapshotDetail)
async def get_performance_snapshot(
    site_id: UUID,
    snapshot_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get detailed performance snapshot."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Verify site belongs to tenant
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    service = PerformanceService(db)
    snapshot = await service.get_snapshot_by_id(snapshot_id, site_id)

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )

    return PerformanceSnapshotDetail.model_validate(snapshot)


@router.post("/sites/{site_id}/analyze", response_model=AnalyzeResponse)
async def trigger_performance_analysis(
    site_id: UUID,
    data: AnalyzeRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("audit:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    """
    Trigger PageSpeed Insights analysis for a site.

    If specific URLs are provided, analyzes those URLs.
    Otherwise, auto-selects top pages per template type.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )

    # Verify site belongs to tenant
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    from app.config import settings

    if not settings.PAGESPEED_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PageSpeed Insights API key not configured",
        )

    # Determine URLs to analyze
    if data.urls:
        urls_with_templates = [(url, "custom") for url in data.urls]
    else:
        # Get pages from latest crawl
        from sqlalchemy import select
        from app.models.crawl import CrawlJob, CrawlPage, JobStatus

        crawl_result = await db.execute(
            select(CrawlJob)
            .where(
                CrawlJob.site_id == site_id,
                CrawlJob.status == JobStatus.COMPLETED,
            )
            .order_by(CrawlJob.completed_at.desc())
            .limit(1)
        )
        crawl = crawl_result.scalar_one_or_none()

        if not crawl:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No completed crawl found. Run a crawl first or provide specific URLs.",
            )

        # Get pages with template types
        pages_result = await db.execute(
            select(CrawlPage)
            .where(
                CrawlPage.crawl_job_id == crawl.id,
                CrawlPage.status_code == 200,
            )
            .limit(500)
        )
        pages = pages_result.scalars().all()

        # Group by template and pick top N
        from collections import defaultdict

        by_template = defaultdict(list)
        for page in pages:
            template = page.template_type or "unknown"
            by_template[template].append(page)

        urls_with_templates = []
        for template, template_pages in by_template.items():
            sorted_pages = sorted(
                template_pages,
                key=lambda x: x.word_count or 0,
                reverse=True,
            )
            for page in sorted_pages[: settings.PAGESPEED_MAX_PAGES_PER_TEMPLATE]:
                urls_with_templates.append((page.url, template))

        # Limit total
        urls_with_templates = urls_with_templates[: data.max_pages]

    if not urls_with_templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No URLs to analyze",
        )

    # Determine strategies
    strategies = None
    if data.strategy == "mobile":
        strategies = ["mobile"]
    elif data.strategy == "desktop":
        strategies = ["desktop"]
    # Default "both" = None (service handles it)

    # Run analysis (could be moved to background task for large batches)
    service = PerformanceService(db)
    snapshots = await service.analyze_urls(
        site_id=site_id,
        tenant_id=current_user.tenant_id,
        urls_with_templates=urls_with_templates,
        strategies=strategies,
    )
    await db.commit()

    return AnalyzeResponse(
        success=True,
        message=f"Analyzed {len(snapshots)} pages",
        pages_queued=len(urls_with_templates),
        urls=[url for url, _ in urls_with_templates],
    )
