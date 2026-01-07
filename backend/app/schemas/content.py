"""
Content schemas.
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.content import PageType, DraftStatus
from app.schemas.common import BaseSchema, IDSchema


class ContentBriefCreate(BaseSchema):
    """Create content brief request."""
    
    keyword_cluster_id: UUID | None = None
    target_keyword: str = Field(min_length=1, max_length=500)
    secondary_keywords: list[str] = []
    search_intent: str | None = None
    page_type: PageType = PageType.BLOG
    word_count_target: int = Field(default=1500, ge=300, le=10000)
    language: str = "en"


class ContentBriefResponse(IDSchema):
    """Content brief response."""
    
    site_id: UUID
    keyword_cluster_id: UUID | None
    target_keyword: str
    secondary_keywords: list[str]
    search_intent: str | None
    suggested_slug: str | None
    page_type: PageType
    outline: dict
    internal_link_suggestions: list[dict]
    word_count_target: int
    tone_guidelines: dict
    language: str
    created_at: datetime
    drafts_count: int = 0


class ContentBriefDetail(ContentBriefResponse):
    """Detailed content brief with drafts."""
    
    drafts: list["ContentDraftResponse"]


class ContentDraftCreate(BaseSchema):
    """Create content draft request."""
    
    content_brief_id: UUID
    generate_full: bool = True


class ContentDraftResponse(IDSchema):
    """Content draft response."""
    
    site_id: UUID
    content_brief_id: UUID
    version: int
    title_tag: str | None
    meta_description: str | None
    h1: str | None
    body_markdown: str | None
    word_count: int | None
    status: DraftStatus
    created_at: datetime
    updated_at: datetime


class ContentDraftUpdate(BaseSchema):
    """Update content draft request."""
    
    title_tag: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)
    h1: str | None = Field(default=None, max_length=255)
    body_markdown: str | None = None
    status: DraftStatus | None = None


class ContentDraftDetail(ContentDraftResponse):
    """Detailed content draft with HTML."""
    
    body_html: str | None
    faq: list[dict]
    brief: ContentBriefResponse | None = None


class ContentGenerationJob(BaseSchema):
    """Content generation job status."""
    
    job_id: UUID
    status: str
    message: str | None = None
    progress: int = 0
