"""
Keyword research endpoints.
"""
from typing import Annotated
from uuid import UUID

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
    KeywordResponse,
)
from app.services.keyword_service import KeywordService
from app.services.site_service import SiteService

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
