"""
Site management endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.site import SiteCreate, SiteResponse, SiteUpdate
from app.services.site_service import SiteService

router = APIRouter(prefix="/sites", tags=["Sites"])


@router.get("", response_model=PaginatedResponse[SiteResponse])
async def list_sites(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
):
    """List sites for the current user's tenant."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )
    
    service = SiteService(db)
    sites, total = await service.list_sites(
        current_user.tenant_id, page, per_page, search
    )
    
    return PaginatedResponse.create(
        items=[SiteResponse.model_validate(s) for s in sites],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    current_user: Annotated[CurrentUser, Depends(require_permission("site:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new site."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant",
        )
    
    service = SiteService(db)
    
    # Check domain uniqueness
    existing = await service.get_by_domain(data.primary_domain, current_user.tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain already registered",
        )
    
    site = await service.create(current_user.tenant_id, data)
    return SiteResponse.model_validate(site)


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a site by ID."""
    service = SiteService(db)
    site = await service.get_by_id(site_id, current_user.tenant_id)
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    return SiteResponse.model_validate(site)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    data: SiteUpdate,
    current_user: Annotated[CurrentUser, Depends(require_permission("site:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a site."""
    service = SiteService(db)
    site = await service.update(site_id, current_user.tenant_id, data)
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    return SiteResponse.model_validate(site)


@router.delete("/{site_id}", response_model=MessageResponse)
async def delete_site(
    site_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("site:delete"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a site."""
    service = SiteService(db)
    deleted = await service.delete(site_id, current_user.tenant_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    
    return MessageResponse(message="Site deleted successfully")
