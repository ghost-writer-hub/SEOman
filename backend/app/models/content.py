"""
Content models for briefs and drafts.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class PageType(str, PyEnum):
    LANDING = "landing"
    BLOG = "blog"
    CATEGORY = "category"
    PRODUCT = "product"
    OTHER = "other"


class DraftStatus(str, PyEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class ContentBrief(Base, BaseModel):
    """Content brief for a target page."""
    
    __tablename__ = "content_briefs"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword_cluster_id = Column(
        UUID(as_uuid=True),
        ForeignKey("keyword_clusters.id"),
        nullable=True,
    )
    target_keyword = Column(String(500), nullable=False)
    secondary_keywords = Column(JSONB, default=list)
    search_intent = Column(String(100), nullable=True)
    suggested_slug = Column(String(255), nullable=True)
    page_type = Column(
        Enum(PageType),
        default=PageType.BLOG,
        nullable=False,
    )
    outline = Column(JSONB, default=dict)
    internal_link_suggestions = Column(JSONB, default=list)
    word_count_target = Column(Integer, default=1500)
    tone_guidelines = Column(JSONB, default=dict)
    language = Column(String(10), default="en")
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Relationships
    site = relationship("Site", back_populates="content_briefs")
    keyword_cluster = relationship("KeywordCluster", back_populates="content_briefs")
    drafts = relationship("ContentDraft", back_populates="content_brief", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ContentBrief {self.target_keyword[:30]}...>"


class ContentDraft(Base, BaseModel):
    """Content draft based on a brief."""
    
    __tablename__ = "content_drafts"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_brief_id = Column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, default=1)
    title_tag = Column(String(70), nullable=True)
    meta_description = Column(String(160), nullable=True)
    h1 = Column(String(255), nullable=True)
    body_markdown = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    faq = Column(JSONB, default=list)
    word_count = Column(Integer, nullable=True)
    status = Column(
        Enum(DraftStatus),
        default=DraftStatus.DRAFT,
        nullable=False,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    updated_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Relationships
    content_brief = relationship("ContentBrief", back_populates="drafts")
    
    def __repr__(self) -> str:
        return f"<ContentDraft v{self.version} ({self.status.value})>"
