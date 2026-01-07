"""
Site service for business logic.
"""
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.site import Site
from app.schemas.site import SiteCreate, SiteUpdate


class SiteService:
    """Service for site operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, site_id: UUID, tenant_id: UUID | None = None) -> Site | None:
        """Get site by ID, optionally filtering by tenant."""
        query = select(Site).where(Site.id == site_id)
        if tenant_id:
            query = query.where(Site.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_domain(self, domain: str, tenant_id: UUID) -> Site | None:
        """Get site by domain within a tenant."""
        result = await self.db.execute(
            select(Site).where(
                Site.primary_domain == domain,
                Site.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def list_sites(
        self,
        tenant_id: UUID,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> tuple[list[Site], int]:
        """List sites for a tenant with pagination."""
        query = select(Site).where(Site.tenant_id == tenant_id)
        count_query = select(func.count(Site.id)).where(Site.tenant_id == tenant_id)
        
        if search:
            search_filter = Site.name.ilike(f"%{search}%") | Site.primary_domain.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(Site.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        sites = result.scalars().all()
        
        return list(sites), total
    
    async def create(self, tenant_id: UUID, data: SiteCreate) -> Site:
        """Create a new site."""
        site = Site(
            tenant_id=tenant_id,
            name=data.name,
            primary_domain=data.primary_domain,
            additional_domains=data.additional_domains,
            default_language=data.default_language,
            target_countries=data.target_countries,
            cms_type=data.cms_type,
            brand_tone=data.brand_tone,
            enabled_features=data.enabled_features,
        )
        self.db.add(site)
        await self.db.flush()
        await self.db.refresh(site)
        return site
    
    async def update(self, site_id: UUID, tenant_id: UUID, data: SiteUpdate) -> Site | None:
        """Update a site."""
        site = await self.get_by_id(site_id, tenant_id)
        if not site:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(site, field, value)
        
        await self.db.flush()
        await self.db.refresh(site)
        return site
    
    async def delete(self, site_id: UUID, tenant_id: UUID) -> bool:
        """Delete a site."""
        site = await self.get_by_id(site_id, tenant_id)
        if not site:
            return False
        
        await self.db.delete(site)
        return True
