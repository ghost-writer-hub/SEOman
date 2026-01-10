"""
Keyword research endpoints.
"""
from typing import Annotated
from uuid import UUID
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.keyword import (
    KeywordClusterDetail,
    KeywordClusterResponse,
    KeywordDiscoverRequest,
    KeywordExpandRequest,
    KeywordJobResponse,
    KeywordRankingResponse,
    KeywordResponse,
    KeywordWithRankingResponse,
    RankingChangesResponse,
    RankingsSummaryResponse,
    SetTrackingRequest,
    SetTrackingResponse,
    TrackTopKeywordsRequest,
    UpdateRankingsResponse,
)
from app.services.keyword_service import KeywordService
from app.services.site_service import SiteService
from app.tasks.keyword_tasks import update_keyword_rankings, track_top_keywords

router = APIRouter(tags=["Keywords"])


@router.post(
    "/sites/{site_id}/keywords/discover",
    response_model=KeywordJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def discover_keywords(
    site_id: UUID,
    data: KeywordDiscoverRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("keyword:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Start keyword discovery for a site."""
    # Verify site access
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    # TODO: Trigger background task
    # from app.tasks.keyword_tasks import discover_keywords_task
    # job_id = discover_keywords_task.delay(str(site_id), data.model_dump())
    
    import uuid
    job_id = uuid.uuid4()
    
    return KeywordJobResponse(
        job_id=job_id,
        status="pending",
        message="Keyword discovery started",
    )


@router.post(
    "/sites/{site_id}/keywords/expand",
    response_model=KeywordJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def expand_keywords(
    site_id: UUID,
    data: KeywordExpandRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("keyword:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Expand keywords from seed keywords."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    import uuid
    job_id = uuid.uuid4()
    
    return KeywordJobResponse(
        job_id=job_id,
        status="pending",
        message="Keyword expansion started",
    )


@router.get("/sites/{site_id}/keywords", response_model=PaginatedResponse[KeywordResponse])
async def list_keywords(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    cluster_id: UUID | None = None,
    search: str | None = None,
):
    """List keywords for a site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    keyword_service = KeywordService(db)
    keywords, total = await keyword_service.list_keywords(
        site_id, page, per_page, cluster_id, search
    )
    
    return PaginatedResponse.create(
        items=[KeywordResponse.model_validate(k) for k in keywords],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/sites/{site_id}/keyword-clusters",
    response_model=PaginatedResponse[KeywordClusterResponse],
)
async def list_clusters(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """List keyword clusters for a site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    keyword_service = KeywordService(db)
    clusters, total = await keyword_service.list_clusters(site_id, page, per_page)
    
    # Add stats to each cluster
    items = []
    for cluster in clusters:
        stats = await keyword_service.get_cluster_stats(cluster.id)
        response = KeywordClusterResponse.model_validate(cluster)
        response.keywords_count = stats["keywords_count"]
        response.total_search_volume = stats["total_search_volume"]
        items.append(response)
    
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/keyword-clusters/{cluster_id}", response_model=KeywordClusterDetail)
async def get_cluster(
    cluster_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get keyword cluster with keywords."""
    keyword_service = KeywordService(db)
    cluster = await keyword_service.get_cluster_by_id(cluster_id)

    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    # Verify access
    site_service = SiteService(db)
    site = await site_service.get_by_id(cluster.site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    stats = await keyword_service.get_cluster_stats(cluster_id)

    response = KeywordClusterDetail.model_validate(cluster)
    response.keywords = [KeywordResponse.model_validate(k) for k in cluster.keywords]
    response.keywords_count = stats["keywords_count"]
    response.total_search_volume = stats["total_search_volume"]

    return response


# Ranking endpoints

@router.get(
    "/sites/{site_id}/rankings",
    response_model=PaginatedResponse[KeywordWithRankingResponse],
)
async def list_tracked_keywords(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
):
    """List tracked keywords with current rankings."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    keyword_service = KeywordService(db)
    keywords, total = await keyword_service.list_tracked_keywords(
        site_id, page, per_page
    )

    return PaginatedResponse.create(
        items=[KeywordWithRankingResponse.from_keyword(k) for k in keywords],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/sites/{site_id}/rankings/summary", response_model=RankingsSummaryResponse)
async def get_rankings_summary(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get ranking summary for a site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    keyword_service = KeywordService(db)
    summary = await keyword_service.get_rankings_summary(site_id)

    return RankingsSummaryResponse(**summary)


@router.get("/sites/{site_id}/rankings/changes", response_model=RankingChangesResponse)
async def get_ranking_changes(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=50),
):
    """Get keywords with biggest ranking changes."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    keyword_service = KeywordService(db)
    changes = await keyword_service.get_ranking_changes(site_id, limit)

    return RankingChangesResponse(
        improved=[KeywordWithRankingResponse.from_keyword(k) for k in changes["improved"]],
        declined=[KeywordWithRankingResponse.from_keyword(k) for k in changes["declined"]],
        new_rankings=[KeywordWithRankingResponse.from_keyword(k) for k in changes["new_rankings"]],
        lost_rankings=[KeywordWithRankingResponse.from_keyword(k) for k in changes["lost_rankings"]],
    )


@router.get(
    "/keywords/{keyword_id}/rankings",
    response_model=list[KeywordRankingResponse],
)
async def get_keyword_ranking_history(
    keyword_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
):
    """Get ranking history for a specific keyword."""
    keyword_service = KeywordService(db)
    keyword = await keyword_service.get_keyword_by_id(keyword_id)

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found",
        )

    # Verify access
    site_service = SiteService(db)
    site = await site_service.get_by_id(keyword.site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    rankings = await keyword_service.get_ranking_history(keyword_id, days)

    return [KeywordRankingResponse.model_validate(r) for r in rankings]


@router.post(
    "/sites/{site_id}/rankings/update",
    response_model=UpdateRankingsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_rankings_update(
    site_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("keyword:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Trigger a rankings update for tracked keywords."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Queue the background task
    task = update_keyword_rankings.delay(str(site_id), str(current_user.tenant_id))

    return UpdateRankingsResponse(
        job_id=uuid_module.UUID(task.id),
        status="pending",
        message="Rankings update started",
    )


@router.post(
    "/sites/{site_id}/keywords/tracking",
    response_model=SetTrackingResponse,
)
async def set_keyword_tracking(
    site_id: UUID,
    data: SetTrackingRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("keyword:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Enable or disable tracking for specific keywords."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    keyword_service = KeywordService(db)
    updated = await keyword_service.set_tracking(data.keyword_ids, data.is_tracked)
    await db.commit()

    return SetTrackingResponse(
        keywords_updated=updated,
        is_tracked=data.is_tracked,
    )


@router.post(
    "/sites/{site_id}/keywords/track-top",
    response_model=KeywordJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def track_top_keywords_endpoint(
    site_id: UUID,
    data: TrackTopKeywordsRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission("keyword:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Automatically enable tracking for top keywords by search volume."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Queue the background task
    task = track_top_keywords.delay(
        str(site_id),
        str(current_user.tenant_id),
        data.limit,
        data.min_volume,
    )

    return KeywordJobResponse(
        job_id=uuid_module.UUID(task.id),
        status="pending",
        message=f"Tracking top {data.limit} keywords with volume >= {data.min_volume}",
    )
