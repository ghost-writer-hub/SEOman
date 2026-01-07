"""
Tenant management endpoints.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import SuperAdmin, get_db
from app.models.tenant import TenantStatus
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    _: SuperAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: TenantStatus | None = None,
):
    """List all tenants (super admin only)."""
    service = TenantService(db)
    tenants, total = await service.list_tenants(page, per_page, status)
    
    return PaginatedResponse.create(
        items=[TenantResponse.model_validate(t) for t in tenants],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    _: SuperAdmin,
    data: TenantCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new tenant (super admin only)."""
    service = TenantService(db)
    
    # Check slug uniqueness
    existing = await service.get_by_slug(data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug already exists",
        )
    
    tenant = await service.create(data)
    return TenantResponse.model_validate(tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    _: SuperAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a tenant by ID (super admin only)."""
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    _: SuperAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a tenant (super admin only)."""
    service = TenantService(db)
    tenant = await service.update(tenant_id, data)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    return TenantResponse.model_validate(tenant)


@router.delete("/{tenant_id}", response_model=MessageResponse)
async def delete_tenant(
    tenant_id: UUID,
    _: SuperAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a tenant (super admin only)."""
    service = TenantService(db)
    deleted = await service.delete(tenant_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    return MessageResponse(message="Tenant deleted successfully")
