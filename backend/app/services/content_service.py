"""
Content service for briefs and drafts.
"""
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import ContentBrief, ContentDraft, DraftStatus
from app.schemas.content import ContentBriefCreate, ContentDraftUpdate


class ContentService:
    """Service for content operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_brief_by_id(self, brief_id: UUID, site_id: UUID | None = None) -> ContentBrief | None:
        """Get content brief by ID."""
        query = select(ContentBrief).where(ContentBrief.id == brief_id)
        if site_id:
            query = query.where(ContentBrief.site_id == site_id)
        query = query.options(selectinload(ContentBrief.drafts))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_briefs(
        self,
        site_id: UUID,
        page: int = 1,
        per_page: int = 20,
        cluster_id: UUID | None = None,
    ) -> tuple[list[ContentBrief], int]:
        """List content briefs for a site."""
        query = select(ContentBrief).where(ContentBrief.site_id == site_id)
        count_query = select(func.count(ContentBrief.id)).where(ContentBrief.site_id == site_id)
        
        if cluster_id:
            query = query.where(ContentBrief.keyword_cluster_id == cluster_id)
            count_query = count_query.where(ContentBrief.keyword_cluster_id == cluster_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(ContentBrief.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        
        return list(result.scalars().all()), total
    
    async def create_brief(
        self,
        site_id: UUID,
        data: ContentBriefCreate,
        user_id: UUID | None = None,
    ) -> ContentBrief:
        """Create a new content brief."""
        brief = ContentBrief(
            site_id=site_id,
            keyword_cluster_id=data.keyword_cluster_id,
            target_keyword=data.target_keyword,
            secondary_keywords=data.secondary_keywords,
            search_intent=data.search_intent,
            page_type=data.page_type,
            word_count_target=data.word_count_target,
            language=data.language,
            created_by_user_id=user_id,
        )
        self.db.add(brief)
        await self.db.flush()
        await self.db.refresh(brief)
        return brief
    
    async def update_brief(
        self,
        brief_id: UUID,
        outline: dict | None = None,
        internal_link_suggestions: list | None = None,
        suggested_slug: str | None = None,
    ) -> ContentBrief | None:
        """Update content brief with generated content."""
        brief = await self.get_brief_by_id(brief_id)
        if not brief:
            return None
        
        if outline is not None:
            brief.outline = outline
        if internal_link_suggestions is not None:
            brief.internal_link_suggestions = internal_link_suggestions
        if suggested_slug is not None:
            brief.suggested_slug = suggested_slug
        
        await self.db.flush()
        await self.db.refresh(brief)
        return brief
    
    async def get_draft_by_id(self, draft_id: UUID) -> ContentDraft | None:
        """Get content draft by ID."""
        result = await self.db.execute(
            select(ContentDraft).where(ContentDraft.id == draft_id)
        )
        return result.scalar_one_or_none()
    
    async def list_drafts(
        self,
        site_id: UUID,
        brief_id: UUID | None = None,
        status: DraftStatus | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ContentDraft], int]:
        """List content drafts."""
        query = select(ContentDraft).where(ContentDraft.site_id == site_id)
        count_query = select(func.count(ContentDraft.id)).where(ContentDraft.site_id == site_id)
        
        if brief_id:
            query = query.where(ContentDraft.content_brief_id == brief_id)
            count_query = count_query.where(ContentDraft.content_brief_id == brief_id)
        if status:
            query = query.where(ContentDraft.status == status)
            count_query = count_query.where(ContentDraft.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(ContentDraft.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        
        return list(result.scalars().all()), total
    
    async def create_draft(
        self,
        site_id: UUID,
        brief_id: UUID,
        user_id: UUID | None = None,
    ) -> ContentDraft:
        """Create a new content draft."""
        # Get latest version
        version_result = await self.db.execute(
            select(func.max(ContentDraft.version))
            .where(ContentDraft.content_brief_id == brief_id)
        )
        latest_version = version_result.scalar() or 0
        
        draft = ContentDraft(
            site_id=site_id,
            content_brief_id=brief_id,
            version=latest_version + 1,
            created_by_user_id=user_id,
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft
    
    async def update_draft(
        self,
        draft_id: UUID,
        data: ContentDraftUpdate,
        user_id: UUID | None = None,
    ) -> ContentDraft | None:
        """Update a content draft."""
        draft = await self.get_draft_by_id(draft_id)
        if not draft:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(draft, field, value)
        
        if user_id:
            draft.updated_by_user_id = user_id
        
        # Calculate word count if body changed
        if data.body_markdown:
            draft.word_count = len(data.body_markdown.split())
        
        await self.db.flush()
        await self.db.refresh(draft)
        return draft
    
    async def save_generated_content(
        self,
        draft_id: UUID,
        title_tag: str,
        meta_description: str,
        h1: str,
        body_markdown: str,
        body_html: str,
        faq: list[dict] | None = None,
    ) -> ContentDraft | None:
        """Save AI-generated content to draft."""
        draft = await self.get_draft_by_id(draft_id)
        if not draft:
            return None
        
        draft.title_tag = title_tag
        draft.meta_description = meta_description
        draft.h1 = h1
        draft.body_markdown = body_markdown
        draft.body_html = body_html
        draft.faq = faq or []
        draft.word_count = len(body_markdown.split())
        
        await self.db.flush()
        await self.db.refresh(draft)
        return draft
