"""
Keyword service for research operations.
"""
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.keyword import Keyword, KeywordCluster, keyword_cluster_members


class KeywordService:
    """Service for keyword operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_keyword_by_id(self, keyword_id: UUID) -> Keyword | None:
        """Get keyword by ID."""
        result = await self.db.execute(
            select(Keyword).where(Keyword.id == keyword_id)
        )
        return result.scalar_one_or_none()
    
    async def list_keywords(
        self,
        site_id: UUID,
        page: int = 1,
        per_page: int = 50,
        cluster_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[Keyword], int]:
        """List keywords for a site."""
        query = select(Keyword).where(Keyword.site_id == site_id)
        count_query = select(func.count(Keyword.id)).where(Keyword.site_id == site_id)
        
        if cluster_id:
            query = query.join(keyword_cluster_members).where(
                keyword_cluster_members.c.cluster_id == cluster_id
            )
            count_query = count_query.join(keyword_cluster_members).where(
                keyword_cluster_members.c.cluster_id == cluster_id
            )
        
        if search:
            query = query.where(Keyword.text.ilike(f"%{search}%"))
            count_query = count_query.where(Keyword.text.ilike(f"%{search}%"))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(Keyword.search_volume.desc().nullslast())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        
        return list(result.scalars().all()), total
    
    async def create_keyword(
        self,
        site_id: UUID,
        text: str,
        language: str = "en",
        country: str = "US",
        **kwargs,
    ) -> Keyword:
        """Create a new keyword."""
        keyword = Keyword(
            site_id=site_id,
            text=text,
            language=language,
            country=country,
            **kwargs,
        )
        self.db.add(keyword)
        await self.db.flush()
        await self.db.refresh(keyword)
        return keyword
    
    async def bulk_create_keywords(
        self,
        site_id: UUID,
        keywords_data: list[dict],
    ) -> list[Keyword]:
        """Create multiple keywords."""
        keywords = []
        for data in keywords_data:
            keyword = Keyword(site_id=site_id, **data)
            self.db.add(keyword)
            keywords.append(keyword)
        
        await self.db.flush()
        for keyword in keywords:
            await self.db.refresh(keyword)
        
        return keywords
    
    async def get_cluster_by_id(self, cluster_id: UUID) -> KeywordCluster | None:
        """Get cluster by ID with keywords."""
        result = await self.db.execute(
            select(KeywordCluster)
            .where(KeywordCluster.id == cluster_id)
            .options(selectinload(KeywordCluster.keywords))
        )
        return result.scalar_one_or_none()
    
    async def list_clusters(
        self,
        site_id: UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[KeywordCluster], int]:
        """List keyword clusters for a site."""
        query = select(KeywordCluster).where(KeywordCluster.site_id == site_id)
        count_query = select(func.count(KeywordCluster.id)).where(
            KeywordCluster.site_id == site_id
        )
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(KeywordCluster.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        
        return list(result.scalars().all()), total
    
    async def create_cluster(
        self,
        site_id: UUID,
        label: str,
        keyword_ids: list[UUID],
        **kwargs,
    ) -> KeywordCluster:
        """Create a keyword cluster with keywords."""
        cluster = KeywordCluster(
            site_id=site_id,
            label=label,
            **kwargs,
        )
        self.db.add(cluster)
        await self.db.flush()
        
        # Add keywords to cluster
        for keyword_id in keyword_ids:
            await self.db.execute(
                keyword_cluster_members.insert().values(
                    keyword_id=keyword_id,
                    cluster_id=cluster.id,
                )
            )
        
        await self.db.refresh(cluster)
        return cluster
    
    async def get_cluster_stats(self, cluster_id: UUID) -> dict:
        """Get statistics for a cluster."""
        # Count keywords
        count_result = await self.db.execute(
            select(func.count(keyword_cluster_members.c.keyword_id)).where(
                keyword_cluster_members.c.cluster_id == cluster_id
            )
        )
        keywords_count = count_result.scalar()
        
        # Sum search volume
        volume_result = await self.db.execute(
            select(func.sum(Keyword.search_volume))
            .join(keyword_cluster_members)
            .where(keyword_cluster_members.c.cluster_id == cluster_id)
        )
        total_volume = volume_result.scalar() or 0
        
        return {
            "keywords_count": keywords_count,
            "total_search_volume": total_volume,
        }
