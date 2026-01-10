"""
Keyword service for research operations.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.keyword import Keyword, KeywordCluster, KeywordRanking, keyword_cluster_members


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

    # Ranking methods

    async def list_tracked_keywords(
        self,
        site_id: UUID,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[Keyword], int]:
        """List tracked keywords for a site with current rankings."""
        query = (
            select(Keyword)
            .where(Keyword.site_id == site_id, Keyword.is_tracked == True)
            .options(selectinload(Keyword.rankings))
        )
        count_query = select(func.count(Keyword.id)).where(
            Keyword.site_id == site_id,
            Keyword.is_tracked == True,
        )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(Keyword.search_volume.desc().nullslast())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def set_tracking(
        self,
        keyword_ids: list[UUID],
        is_tracked: bool,
    ) -> int:
        """Enable or disable tracking for keywords."""
        updated = 0
        for keyword_id in keyword_ids:
            keyword = await self.db.get(Keyword, keyword_id)
            if keyword:
                keyword.is_tracked = is_tracked
                updated += 1

        await self.db.flush()
        return updated

    async def get_ranking_history(
        self,
        keyword_id: UUID,
        days: int = 30,
    ) -> list[KeywordRanking]:
        """Get ranking history for a keyword."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(KeywordRanking)
            .where(
                KeywordRanking.keyword_id == keyword_id,
                KeywordRanking.checked_at >= since,
            )
            .order_by(desc(KeywordRanking.checked_at))
        )
        return list(result.scalars().all())

    async def get_rankings_summary(
        self,
        site_id: UUID,
    ) -> dict:
        """Get ranking summary for a site."""
        # Count tracked keywords
        tracked_count = await self.db.execute(
            select(func.count(Keyword.id)).where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
            )
        )
        total_tracked = tracked_count.scalar() or 0

        # Count keywords in top 10
        top_10_count = await self.db.execute(
            select(func.count(Keyword.id)).where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position <= 10,
                Keyword.current_position.isnot(None),
            )
        )
        in_top_10 = top_10_count.scalar() or 0

        # Count keywords in top 3
        top_3_count = await self.db.execute(
            select(func.count(Keyword.id)).where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position <= 3,
                Keyword.current_position.isnot(None),
            )
        )
        in_top_3 = top_3_count.scalar() or 0

        # Count keywords not ranking (position is None)
        not_ranking_count = await self.db.execute(
            select(func.count(Keyword.id)).where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.is_(None),
            )
        )
        not_ranking = not_ranking_count.scalar() or 0

        # Count improved keywords (current < previous)
        improved_count = await self.db.execute(
            select(func.count(Keyword.id)).where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.isnot(None),
                Keyword.previous_position.isnot(None),
                Keyword.current_position < Keyword.previous_position,
            )
        )
        improved = improved_count.scalar() or 0

        # Count declined keywords (current > previous)
        declined_count = await self.db.execute(
            select(func.count(Keyword.id)).where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.isnot(None),
                Keyword.previous_position.isnot(None),
                Keyword.current_position > Keyword.previous_position,
            )
        )
        declined = declined_count.scalar() or 0

        # Calculate average position
        avg_position = await self.db.execute(
            select(func.avg(Keyword.current_position)).where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.isnot(None),
            )
        )
        average_position = avg_position.scalar()

        return {
            "total_tracked": total_tracked,
            "in_top_3": in_top_3,
            "in_top_10": in_top_10,
            "not_ranking": not_ranking,
            "improved": improved,
            "declined": declined,
            "average_position": round(average_position, 1) if average_position else None,
        }

    async def get_ranking_changes(
        self,
        site_id: UUID,
        limit: int = 20,
    ) -> dict:
        """Get keywords with biggest ranking changes."""
        # Keywords that improved the most
        improved_query = (
            select(Keyword)
            .where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.isnot(None),
                Keyword.previous_position.isnot(None),
                Keyword.current_position < Keyword.previous_position,
            )
            .order_by((Keyword.previous_position - Keyword.current_position).desc())
            .limit(limit)
        )
        improved_result = await self.db.execute(improved_query)
        improved = list(improved_result.scalars().all())

        # Keywords that declined the most
        declined_query = (
            select(Keyword)
            .where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.isnot(None),
                Keyword.previous_position.isnot(None),
                Keyword.current_position > Keyword.previous_position,
            )
            .order_by((Keyword.current_position - Keyword.previous_position).desc())
            .limit(limit)
        )
        declined_result = await self.db.execute(declined_query)
        declined = list(declined_result.scalars().all())

        # New rankings (previous was None, current is not)
        new_rankings_query = (
            select(Keyword)
            .where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.isnot(None),
                Keyword.previous_position.is_(None),
            )
            .order_by(Keyword.current_position)
            .limit(limit)
        )
        new_result = await self.db.execute(new_rankings_query)
        new_rankings = list(new_result.scalars().all())

        # Lost rankings (previous was not None, current is None)
        lost_rankings_query = (
            select(Keyword)
            .where(
                Keyword.site_id == site_id,
                Keyword.is_tracked == True,
                Keyword.current_position.is_(None),
                Keyword.previous_position.isnot(None),
            )
            .order_by(Keyword.previous_position)
            .limit(limit)
        )
        lost_result = await self.db.execute(lost_rankings_query)
        lost_rankings = list(lost_result.scalars().all())

        return {
            "improved": improved,
            "declined": declined,
            "new_rankings": new_rankings,
            "lost_rankings": lost_rankings,
        }
