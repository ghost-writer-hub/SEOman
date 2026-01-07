"""
Content Tasks

Background tasks for content generation and management.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.content import ContentBrief, ContentDraft, ContentStatus
from app.models.keyword import Keyword, KeywordCluster
from app.models.site import Site
from app.integrations.llm import get_llm_client, generate_content_brief, Message
from app.integrations.storage import get_storage_client, SEOmanStoragePaths


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(bind=True, max_retries=3)
def generate_brief(
    self,
    brief_id: str,
    site_id: str,
    tenant_id: str,
):
    """Generate a content brief using AI."""
    return run_async(_generate_brief(self, brief_id, site_id, tenant_id))


async def _generate_brief(task, brief_id: str, site_id: str, tenant_id: str):
    """Async implementation of brief generation."""
    async with async_session_maker() as session:
        brief = await session.get(ContentBrief, UUID(brief_id))
        site = await session.get(Site, UUID(site_id))
        
        if not brief or not site:
            return {"error": "Brief or site not found"}
        
        try:
            llm = get_llm_client()
            
            if not await llm.health_check():
                raise Exception("LLM service unavailable")
            
            # Generate brief using LLM
            result = await generate_content_brief(
                llm,
                keyword=brief.target_keyword,
                competitors=[],  # TODO: Add competitor analysis
            )
            
            # Update brief with generated content
            brief.title_suggestions = result.get("title_suggestions", [])
            brief.meta_description = result.get("meta_description")
            brief.target_word_count = result.get("target_word_count", 1500)
            brief.content_outline = result.get("content_outline", [])
            brief.keywords_to_include = result.get("keywords_to_include", [])
            brief.internal_links = result.get("internal_linking_suggestions", [])
            brief.status = ContentStatus.READY
            brief.updated_at = datetime.utcnow()
            
            await session.commit()
            
            # Store brief in object storage
            try:
                storage = get_storage_client()
                brief_path = SEOmanStoragePaths.content_brief(
                    tenant_id, site_id, brief_id
                )
                storage.upload_json(brief_path, {
                    "brief_id": brief_id,
                    "target_keyword": brief.target_keyword,
                    "title_suggestions": brief.title_suggestions,
                    "meta_description": brief.meta_description,
                    "content_outline": brief.content_outline,
                    "keywords_to_include": brief.keywords_to_include,
                    "generated_at": datetime.utcnow().isoformat(),
                })
            except Exception:
                pass  # Storage is optional
            
            return {
                "brief_id": brief_id,
                "status": "ready",
                "title_suggestions": len(brief.title_suggestions or []),
            }
            
        except Exception as e:
            brief.status = ContentStatus.FAILED
            brief.error_message = str(e)
            await session.commit()
            
            raise task.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_draft(
    self,
    draft_id: str,
    brief_id: str,
    site_id: str,
    tenant_id: str,
):
    """Generate a content draft from a brief."""
    return run_async(_generate_draft(self, draft_id, brief_id, site_id, tenant_id))


async def _generate_draft(
    task,
    draft_id: str,
    brief_id: str,
    site_id: str,
    tenant_id: str,
):
    """Async implementation of draft generation."""
    async with async_session_maker() as session:
        draft = await session.get(ContentDraft, UUID(draft_id))
        brief = await session.get(ContentBrief, UUID(brief_id))
        
        if not draft or not brief:
            return {"error": "Draft or brief not found"}
        
        try:
            llm = get_llm_client()
            
            if not await llm.health_check():
                raise Exception("LLM service unavailable")
            
            # Build prompt from brief
            outline_text = ""
            for section in (brief.content_outline or []):
                outline_text += f"\n## {section.get('heading', 'Section')}\n"
                for point in section.get("key_points", []):
                    outline_text += f"- {point}\n"
            
            keywords_text = ", ".join(brief.keywords_to_include or [])
            
            prompt = f"""Write a comprehensive, SEO-optimized article based on this brief:

Target Keyword: {brief.target_keyword}
Target Word Count: {brief.target_word_count or 1500} words
Keywords to Include: {keywords_text}

Content Outline:
{outline_text}

Requirements:
1. Write in a professional but engaging tone
2. Include the target keyword naturally throughout
3. Use the provided outline as structure
4. Include an introduction and conclusion
5. Make it informative and valuable to readers
6. Format with markdown headings and lists where appropriate

Write the full article now:"""
            
            messages = [
                Message(
                    role="system",
                    content="You are an expert content writer specializing in SEO-optimized articles. "
                            "Write high-quality, engaging content that ranks well in search engines.",
                ),
                Message(role="user", content=prompt),
            ]
            
            response = await llm.chat(messages, max_tokens=4000)
            
            # Update draft
            draft.content = response.content
            draft.word_count = len(response.content.split())
            draft.status = ContentStatus.DRAFT
            draft.updated_at = datetime.utcnow()
            
            await session.commit()
            
            # Store draft in object storage
            try:
                storage = get_storage_client()
                draft_path = SEOmanStoragePaths.content_draft(
                    tenant_id, site_id, brief_id, draft_id
                )
                storage.upload_bytes(
                    draft_path,
                    response.content.encode("utf-8"),
                    content_type="text/markdown",
                )
            except Exception:
                pass
            
            return {
                "draft_id": draft_id,
                "status": "draft",
                "word_count": draft.word_count,
            }
            
        except Exception as e:
            draft.status = ContentStatus.FAILED
            draft.error_message = str(e)
            await session.commit()
            
            raise task.retry(exc=e, countdown=60)


@shared_task(bind=True)
def improve_draft(
    self,
    draft_id: str,
    instructions: str,
):
    """Improve an existing draft based on feedback."""
    return run_async(_improve_draft(draft_id, instructions))


async def _improve_draft(draft_id: str, instructions: str):
    """Use LLM to improve draft based on instructions."""
    async with async_session_maker() as session:
        draft = await session.get(ContentDraft, UUID(draft_id))
        
        if not draft:
            return {"error": "Draft not found"}
        
        try:
            llm = get_llm_client()
            
            if not await llm.health_check():
                return {"error": "LLM service unavailable"}
            
            prompt = f"""Improve the following article based on these instructions:

Instructions: {instructions}

Current Article:
{draft.content}

Rewrite the article incorporating the requested improvements:"""
            
            messages = [
                Message(
                    role="system",
                    content="You are an expert editor who improves content while maintaining SEO optimization.",
                ),
                Message(role="user", content=prompt),
            ]
            
            response = await llm.chat(messages, max_tokens=4000)
            
            # Update draft
            draft.content = response.content
            draft.word_count = len(response.content.split())
            draft.version = (draft.version or 1) + 1
            draft.updated_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "draft_id": draft_id,
                "version": draft.version,
                "word_count": draft.word_count,
            }
            
        except Exception as e:
            return {"error": str(e)}


@shared_task(bind=True)
def analyze_content_seo(self, draft_id: str):
    """Analyze draft content for SEO optimization."""
    return run_async(_analyze_content_seo(draft_id))


async def _analyze_content_seo(draft_id: str) -> Dict[str, Any]:
    """Check content for SEO best practices."""
    async with async_session_maker() as session:
        draft = await session.get(ContentDraft, UUID(draft_id))
        
        if not draft:
            return {"error": "Draft not found"}
        
        brief = await session.get(ContentBrief, draft.brief_id)
        
        content = draft.content or ""
        target_keyword = brief.target_keyword if brief else ""
        
        # Basic SEO analysis
        analysis = {
            "word_count": len(content.split()),
            "keyword_density": 0,
            "has_h1": "# " in content,
            "heading_count": content.count("\n#"),
            "issues": [],
            "score": 100,
        }
        
        # Check keyword usage
        if target_keyword:
            keyword_count = content.lower().count(target_keyword.lower())
            word_count = analysis["word_count"]
            if word_count > 0:
                analysis["keyword_density"] = round(
                    (keyword_count / word_count) * 100, 2
                )
        
        # Check word count
        target_count = brief.target_word_count if brief else 1500
        if analysis["word_count"] < target_count * 0.8:
            analysis["issues"].append({
                "type": "word_count",
                "message": f"Content is too short. Target: {target_count}, Current: {analysis['word_count']}",
                "severity": "medium",
            })
            analysis["score"] -= 10
        
        # Check keyword density
        if analysis["keyword_density"] < 0.5:
            analysis["issues"].append({
                "type": "keyword_density",
                "message": "Keyword density is too low. Consider using the target keyword more.",
                "severity": "medium",
            })
            analysis["score"] -= 10
        elif analysis["keyword_density"] > 3:
            analysis["issues"].append({
                "type": "keyword_stuffing",
                "message": "Keyword density is too high. This may be seen as keyword stuffing.",
                "severity": "high",
            })
            analysis["score"] -= 20
        
        # Check headings
        if not analysis["has_h1"]:
            analysis["issues"].append({
                "type": "missing_h1",
                "message": "Content is missing an H1 heading.",
                "severity": "high",
            })
            analysis["score"] -= 15
        
        if analysis["heading_count"] < 3:
            analysis["issues"].append({
                "type": "few_headings",
                "message": "Content has few headings. Add more structure.",
                "severity": "low",
            })
            analysis["score"] -= 5
        
        return analysis


@shared_task(bind=True)
def batch_generate_briefs(
    self,
    site_id: str,
    tenant_id: str,
    keyword_ids: List[str],
):
    """Generate briefs for multiple keywords."""
    return run_async(_batch_generate_briefs(site_id, tenant_id, keyword_ids))


async def _batch_generate_briefs(
    site_id: str,
    tenant_id: str,
    keyword_ids: List[str],
):
    """Create and queue briefs for multiple keywords."""
    async with async_session_maker() as session:
        briefs_created = 0
        
        for keyword_id in keyword_ids:
            keyword = await session.get(Keyword, UUID(keyword_id))
            
            if not keyword:
                continue
            
            # Create brief
            brief = ContentBrief(
                site_id=UUID(site_id),
                tenant_id=UUID(tenant_id),
                target_keyword=keyword.keyword,
                status=ContentStatus.PENDING,
            )
            session.add(brief)
            await session.flush()
            
            # Queue generation
            generate_brief.delay(str(brief.id), site_id, tenant_id)
            briefs_created += 1
        
        await session.commit()
        
        return {
            "site_id": site_id,
            "briefs_created": briefs_created,
        }
