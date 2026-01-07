"""
Content generation endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, require_permission
from app.models.content import DraftStatus
from app.schemas.common import PaginatedResponse
from app.schemas.content import (
    ContentBriefCreate,
    ContentBriefDetail,
    ContentBriefResponse,
    ContentDraftCreate,
    ContentDraftDetail,
    ContentDraftResponse,
    ContentDraftUpdate,
    ContentGenerationJob,
)
from app.services.content_service import ContentService
from app.services.site_service import SiteService

router = APIRouter(tags=["Content"])


@router.post(
    "/sites/{site_id}/content/briefs",
    response_model=ContentBriefResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_brief(
    site_id: UUID,
    data: ContentBriefCreate,
    current_user: Annotated[CurrentUser, Depends(require_permission("content:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new content brief."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    content_service = ContentService(db)
    brief = await content_service.create_brief(site_id, data, current_user.id)
    
    # TODO: Trigger background task to generate outline
    # from app.tasks.content_tasks import generate_brief_outline
    # generate_brief_outline.delay(str(brief.id))
    
    return ContentBriefResponse.model_validate(brief)


@router.get(
    "/sites/{site_id}/content/briefs",
    response_model=PaginatedResponse[ContentBriefResponse],
)
async def list_briefs(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    cluster_id: UUID | None = None,
):
    """List content briefs for a site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    content_service = ContentService(db)
    briefs, total = await content_service.list_briefs(site_id, page, per_page, cluster_id)
    
    return PaginatedResponse.create(
        items=[ContentBriefResponse.model_validate(b) for b in briefs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/briefs/{brief_id}", response_model=ContentBriefDetail)
async def get_brief(
    brief_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get content brief with drafts."""
    content_service = ContentService(db)
    brief = await content_service.get_brief_by_id(brief_id)
    
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brief not found",
        )
    
    # Verify access
    site_service = SiteService(db)
    site = await site_service.get_by_id(brief.site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    response = ContentBriefDetail.model_validate(brief)
    response.drafts = [ContentDraftResponse.model_validate(d) for d in brief.drafts]
    response.drafts_count = len(brief.drafts)
    
    return response


@router.post(
    "/briefs/{brief_id}/drafts",
    response_model=ContentGenerationJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_draft(
    brief_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("content:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    generate_full: bool = Query(default=True),
):
    """Create a new draft from a brief and optionally generate content."""
    content_service = ContentService(db)
    brief = await content_service.get_brief_by_id(brief_id)
    
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brief not found",
        )
    
    # Verify access
    site_service = SiteService(db)
    site = await site_service.get_by_id(brief.site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    draft = await content_service.create_draft(brief.site_id, brief_id, current_user.id)
    
    # TODO: Trigger background task to generate content
    # if generate_full:
    #     from app.tasks.content_tasks import generate_draft_content
    #     generate_draft_content.delay(str(draft.id))
    
    return ContentGenerationJob(
        job_id=draft.id,
        status="pending" if generate_full else "ready",
        message="Content generation started" if generate_full else "Draft created",
    )


@router.get(
    "/sites/{site_id}/content/drafts",
    response_model=PaginatedResponse[ContentDraftResponse],
)
async def list_drafts(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: DraftStatus | None = None,
):
    """List content drafts for a site."""
    site_service = SiteService(db)
    site = await site_service.get_by_id(site_id, current_user.tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    content_service = ContentService(db)
    drafts, total = await content_service.list_drafts(site_id, status=status, page=page, per_page=per_page)
    
    return PaginatedResponse.create(
        items=[ContentDraftResponse.model_validate(d) for d in drafts],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/drafts/{draft_id}", response_model=ContentDraftDetail)
async def get_draft(
    draft_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get content draft details."""
    content_service = ContentService(db)
    draft = await content_service.get_draft_by_id(draft_id)
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    
    return ContentDraftDetail.model_validate(draft)


@router.patch("/drafts/{draft_id}", response_model=ContentDraftResponse)
async def update_draft(
    draft_id: UUID,
    data: ContentDraftUpdate,
    current_user: Annotated[CurrentUser, Depends(require_permission("content:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a content draft."""
    content_service = ContentService(db)
    draft = await content_service.update_draft(draft_id, data, current_user.id)
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    
    return ContentDraftResponse.model_validate(draft)
