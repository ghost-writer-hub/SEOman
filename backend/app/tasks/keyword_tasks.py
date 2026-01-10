"""
Keyword Tasks

Background tasks for keyword research and tracking.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.keyword import Keyword, KeywordCluster, KeywordGap, KeywordRanking
from app.models.site import Site
from app.integrations.dataforseo import DataForSEOClient
from app.integrations.llm import get_llm_client, cluster_keywords

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(bind=True, max_retries=3)
def discover_keywords(
    self,
    site_id: str,
    tenant_id: str,
    seed_keywords: List[str],
    location: str = "United States",
    language: str = "en",
):
    """Discover new keywords from seed keywords."""
    return run_async(_discover_keywords(
        self, site_id, tenant_id, seed_keywords, location, language
    ))


async def _discover_keywords(
    task,
    site_id: str,
    tenant_id: str,
    seed_keywords: List[str],
    location: str,
    language: str,
):
    """Async implementation of keyword discovery."""
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))
        
        if not site:
            return {"error": "Site not found"}
        
        try:
            client = DataForSEOClient()
            
            all_keywords = []
            
            for seed in seed_keywords:
                # Get keyword ideas
                result = await client.get_keyword_ideas(
                    keyword=seed,
                    location_name=location,
                    language_code=language,
                    limit=100,
                )
                
                if result.get("success"):
                    keywords_data = result.get("keywords", [])
                    all_keywords.extend(keywords_data)
            
            seen: set[str] = set()
            unique_keywords = []
            for kw in all_keywords:
                text = (kw.get("text") or kw.get("keyword", "")).lower()
                if text and text not in seen:
                    seen.add(text)
                    unique_keywords.append(kw)
            
            saved_count = 0
            for kw_data in unique_keywords:
                kw_text = kw_data.get("text") or kw_data.get("keyword", "")
                stmt = select(Keyword).where(
                    Keyword.site_id == site.id,
                    Keyword.text == kw_text,
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing.search_volume = kw_data.get("search_volume")
                    existing.cpc = kw_data.get("cpc")
                    existing.competition = kw_data.get("competition")
                    existing.updated_at = datetime.utcnow()
                else:
                    keyword = Keyword(
                        site_id=site.id,
                        text=kw_text,
                        search_volume=kw_data.get("search_volume"),
                        cpc=kw_data.get("cpc"),
                        competition=kw_data.get("competition"),
                        difficulty=kw_data.get("difficulty"),
                        intent=kw_data.get("intent"),
                    )
                    session.add(keyword)
                    saved_count += 1
            
            await session.commit()
            
            return {
                "site_id": site_id,
                "keywords_discovered": len(unique_keywords),
                "new_keywords_saved": saved_count,
            }
            
        except Exception as e:
            raise task.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def update_keyword_rankings(self, site_id: str, tenant_id: str):
    """Update rankings for all tracked keywords of a site."""
    return run_async(_update_keyword_rankings(self, site_id, tenant_id))


async def _update_keyword_rankings(task, site_id: str, tenant_id: str):
    """
    Check current rankings for site keywords.

    For each tracked keyword:
    1. Fetch SERP results from DataForSEO
    2. Find the site's position in organic results
    3. Store historical ranking data
    4. Update keyword's current/previous position
    5. Track best position achieved
    """
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))

        if not site:
            return {"error": "Site not found"}

        # Get tracked keywords
        stmt = select(Keyword).where(
            Keyword.site_id == site.id,
            Keyword.is_tracked == True,
        )
        result = await session.execute(stmt)
        keywords = result.scalars().all()

        if not keywords:
            return {"message": "No tracked keywords found", "site_id": site_id}

        logger.info(f"Checking rankings for {len(keywords)} keywords on site {site.primary_domain}")

        try:
            client = DataForSEOClient()
            now = datetime.now(timezone.utc)

            updated = 0
            rankings_created = 0
            errors = []

            # Process keywords in batches
            keyword_texts = [kw.text for kw in keywords]
            keyword_map = {kw.text: kw for kw in keywords}

            # Get the primary domain for matching
            primary_domain = site.primary_domain.lower()
            if primary_domain.startswith("www."):
                primary_domain = primary_domain[4:]

            # Fetch SERP data in batches
            serp_results = await client.get_rankings_batch(
                keywords=keyword_texts,
                country=site.target_countries[0] if site.target_countries else "US",
                language=site.default_language or "en",
                batch_size=10,
            )

            for serp_result in serp_results:
                keyword_text = serp_result.get("keyword")
                keyword = keyword_map.get(keyword_text)

                if not keyword:
                    continue

                if not serp_result.get("success"):
                    errors.append({
                        "keyword": keyword_text,
                        "error": serp_result.get("error", "Unknown error"),
                    })
                    continue

                organic = serp_result.get("organic", [])
                serp_features = serp_result.get("serp_features", {})
                competitor_positions = serp_result.get("competitor_positions", [])

                # Find our position in organic results
                position = None
                ranking_url = None

                for item in organic:
                    item_domain = item.get("domain", "").lower()
                    if item_domain.startswith("www."):
                        item_domain = item_domain[4:]

                    if item_domain == primary_domain:
                        position = item.get("position")
                        ranking_url = item.get("url")
                        break

                # Store previous position before updating
                previous_position = keyword.current_position

                # Update keyword with new ranking data
                keyword.previous_position = previous_position
                keyword.current_position = position
                keyword.ranking_url = ranking_url
                keyword.last_checked_at = now

                # Update best position if this is better
                if position is not None:
                    if keyword.best_position is None or position < keyword.best_position:
                        keyword.best_position = position

                # Create historical ranking record
                ranking = KeywordRanking(
                    keyword_id=keyword.id,
                    site_id=site.id,
                    position=position,
                    url=ranking_url,
                    serp_features=serp_features,
                    competitor_positions=competitor_positions,
                    checked_at=now,
                )
                session.add(ranking)
                rankings_created += 1
                updated += 1

            await session.commit()

            logger.info(
                f"Rankings updated for site {site.primary_domain}: "
                f"{updated} keywords updated, {rankings_created} historical records created"
            )

            return {
                "site_id": site_id,
                "domain": site.primary_domain,
                "keywords_checked": len(keywords),
                "keywords_updated": updated,
                "rankings_created": rankings_created,
                "errors": errors[:10] if errors else [],
                "checked_at": now.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error updating rankings for site {site_id}: {e}")
            raise task.retry(exc=e, countdown=120)


@shared_task(bind=True)
def update_all_rankings(self):
    """Update rankings for all sites (scheduled task)."""
    return run_async(_update_all_rankings())


async def _update_all_rankings():
    """Check rankings for all sites with tracked keywords."""
    async with async_session_maker() as session:
        # Get all sites with tracked keywords
        stmt = (
            select(Site)
            .join(Keyword)
            .where(Keyword.is_tracked == True)
            .distinct()
        )
        result = await session.execute(stmt)
        sites = result.scalars().all()

        logger.info(f"Queueing ranking updates for {len(sites)} sites")

        for site in sites:
            # Queue individual update tasks
            update_keyword_rankings.delay(str(site.id), str(site.tenant_id))

        return {
            "sites_queued": len(sites),
            "site_ids": [str(s.id) for s in sites],
        }


@shared_task(bind=True)
def set_keyword_tracking(
    self,
    site_id: str,
    keyword_ids: List[str],
    is_tracked: bool,
    tenant_id: str,
):
    """Enable or disable tracking for specific keywords."""
    return run_async(_set_keyword_tracking(site_id, keyword_ids, is_tracked))


async def _set_keyword_tracking(
    site_id: str,
    keyword_ids: List[str],
    is_tracked: bool,
):
    """Update tracking status for keywords."""
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))

        if not site:
            return {"error": "Site not found"}

        updated = 0
        for keyword_id in keyword_ids:
            keyword = await session.get(Keyword, UUID(keyword_id))
            if keyword and keyword.site_id == site.id:
                keyword.is_tracked = is_tracked
                updated += 1

        await session.commit()

        logger.info(
            f"Updated tracking for {updated} keywords on site {site.primary_domain} "
            f"(is_tracked={is_tracked})"
        )

        return {
            "site_id": site_id,
            "keywords_updated": updated,
            "is_tracked": is_tracked,
        }


@shared_task(bind=True)
def track_top_keywords(
    self,
    site_id: str,
    tenant_id: str,
    limit: int = 50,
    min_volume: int = 100,
):
    """Automatically track top keywords by search volume."""
    return run_async(_track_top_keywords(site_id, limit, min_volume))


async def _track_top_keywords(site_id: str, limit: int, min_volume: int):
    """Enable tracking for top keywords by search volume."""
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))

        if not site:
            return {"error": "Site not found"}

        # Get top keywords by volume that aren't already tracked
        stmt = (
            select(Keyword)
            .where(
                Keyword.site_id == site.id,
                Keyword.is_tracked == False,
                Keyword.search_volume >= min_volume,
            )
            .order_by(Keyword.search_volume.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        keywords = result.scalars().all()

        for keyword in keywords:
            keyword.is_tracked = True

        await session.commit()

        logger.info(
            f"Enabled tracking for {len(keywords)} top keywords on site {site.primary_domain}"
        )

        return {
            "site_id": site_id,
            "keywords_tracked": len(keywords),
            "keywords": [{"id": str(k.id), "text": k.text, "volume": k.search_volume} for k in keywords[:10]],
        }


@shared_task(bind=True)
def cluster_site_keywords(self, site_id: str, tenant_id: str):
    """Cluster keywords for a site using AI."""
    return run_async(_cluster_site_keywords(site_id, tenant_id))


async def _cluster_site_keywords(site_id: str, tenant_id: str):
    """Use LLM to cluster keywords by topic and intent."""
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))
        
        if not site:
            return {"error": "Site not found"}
        
        # Get all keywords for site
        stmt = select(Keyword).where(Keyword.site_id == site.id)
        result = await session.execute(stmt)
        keywords = result.scalars().all()
        
        if len(keywords) < 3:
            return {"message": "Not enough keywords to cluster"}
        
        keyword_texts = [str(kw.text) for kw in keywords]
        
        try:
            llm = get_llm_client()
            
            if not await llm.health_check():
                return {"error": "LLM service unavailable"}
            
            # Use LLM to cluster
            cluster_result = await cluster_keywords(llm, keyword_texts)
            
            clusters_created = 0
            for cluster_data in cluster_result.get("clusters", []):
                cluster = KeywordCluster(
                    site_id=site.id,
                    label=cluster_data.get("name", "Unnamed Cluster"),
                    description=cluster_data.get("description"),
                )
                session.add(cluster)
                await session.flush()
                
                cluster_keyword_texts = [k.lower() for k in cluster_data.get("keywords", [])]
                for kw in keywords:
                    if str(kw.text).lower() in cluster_keyword_texts:
                        kw.clusters.append(cluster)
                
                clusters_created += 1
            
            await session.commit()
            
            return {
                "site_id": site_id,
                "clusters_created": clusters_created,
                "keywords_clustered": len(keywords),
            }
            
        except Exception as e:
            return {"error": str(e)}


@shared_task(bind=True)
def analyze_keyword_gaps(
    self,
    site_id: str,
    competitor_urls: List[str],
    tenant_id: str,
):
    """Find keyword gaps compared to competitors."""
    return run_async(_analyze_keyword_gaps(site_id, competitor_urls, tenant_id))


async def _analyze_keyword_gaps(
    site_id: str,
    competitor_urls: List[str],
    tenant_id: str,
):
    """Identify keywords competitors rank for that we don't."""
    async with async_session_maker() as session:
        site = await session.get(Site, UUID(site_id))
        
        if not site:
            return {"error": "Site not found"}
        
        try:
            client = DataForSEOClient()
            
            our_keywords: set[str] = set()
            our_data = await client.keywords_for_site(
                domain=str(site.primary_domain),
                country="US",
                limit=500,
            )
            for kw in our_data:
                if kw.get("text"):
                    our_keywords.add(kw["text"].lower())
            
            competitor_keywords: Dict[str, Dict[str, Any]] = {}
            for comp_url in competitor_urls:
                comp_domain = comp_url.replace("https://", "").replace("http://", "").split("/")[0]
                comp_data = await client.keywords_for_site(
                    domain=comp_domain,
                    country="US",
                    limit=500,
                )
                for kw in comp_data:
                    text = kw.get("text", "").lower()
                    if not text:
                        continue
                    if text not in competitor_keywords:
                        competitor_keywords[text] = {
                            "keyword": text,
                            "search_volume": kw.get("search_volume", 0),
                            "difficulty": kw.get("difficulty"),
                            "intent": kw.get("intent"),
                            "competitors": [],
                        }
                    competitor_keywords[text]["competitors"].append(comp_domain)
            
            gaps = []
            for kw_text, data in competitor_keywords.items():
                if kw_text not in our_keywords and data["search_volume"] and data["search_volume"] > 50:
                    priority = data["search_volume"] * len(data["competitors"])
                    if data["difficulty"] and data["difficulty"] < 50:
                        priority *= 1.5
                    gaps.append({
                        "keyword": data["keyword"],
                        "search_volume": data["search_volume"],
                        "difficulty": data["difficulty"],
                        "intent": data["intent"],
                        "competitor_count": len(data["competitors"]),
                        "competitors": data["competitors"],
                        "priority_score": priority,
                    })
            
            gaps.sort(key=lambda x: x["priority_score"], reverse=True)
            gaps = gaps[:100]
            
            for gap in gaps:
                stmt = select(KeywordGap).where(
                    KeywordGap.site_id == site.id,
                    KeywordGap.keyword == gap["keyword"],
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing.search_volume = gap["search_volume"]
                    existing.difficulty = gap["difficulty"]
                    existing.intent = gap["intent"]
                    existing.competitor_count = gap["competitor_count"]
                    existing.competitors = gap["competitors"]
                    existing.priority_score = gap["priority_score"]
                else:
                    keyword_gap = KeywordGap(
                        site_id=site.id,
                        keyword=gap["keyword"],
                        search_volume=gap["search_volume"],
                        difficulty=gap["difficulty"],
                        intent=gap["intent"],
                        competitor_count=gap["competitor_count"],
                        competitors=gap["competitors"],
                        priority_score=gap["priority_score"],
                    )
                    session.add(keyword_gap)
            
            await session.commit()
            
            return {
                "site_id": site_id,
                "competitors_analyzed": len(competitor_urls),
                "gaps_found": len(gaps),
                "top_gaps": gaps[:10],
            }
            
        except Exception as e:
            return {"error": str(e)}
