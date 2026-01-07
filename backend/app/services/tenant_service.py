"""
Tenant service for business logic.
"""
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantStatus
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    """Service for tenant operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by slug."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def list_tenants(
        self,
        page: int = 1,
        per_page: int = 20,
        status: TenantStatus | None = None,
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination."""
        query = select(Tenant)
        count_query = select(func.count(Tenant.id))
        
        if status:
            query = query.where(Tenant.status == status)
            count_query = count_query.where(Tenant.status == status)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        tenants = result.scalars().all()
        
        return list(tenants), total
    
    async def create(self, data: TenantCreate) -> Tenant:
        """Create a new tenant."""
        tenant = Tenant(
            name=data.name,
            slug=data.slug,
            plan=data.plan,
        )
        self.db.add(tenant)
        await self.db.flush()
        await self.db.refresh(tenant)
        return tenant
    
    async def update(self, tenant_id: UUID, data: TenantUpdate) -> Tenant | None:
        """Update a tenant."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        await self.db.flush()
        await self.db.refresh(tenant)
        return tenant
    
    async def delete(self, tenant_id: UUID) -> bool:
        """Delete a tenant."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False
        
        await self.db.delete(tenant)
        return True
