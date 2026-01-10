"""
Keyword models for SEO keyword research.
"""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class Keyword(Base, BaseModel):
    """Keyword data from research."""

    __tablename__ = "keywords"

    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = Column(String(500), nullable=False)
    language = Column(String(10), default="en")
    country = Column(String(10), default="US")
    search_volume = Column(Integer, nullable=True)
    cpc = Column(Numeric(10, 2), nullable=True)
    competition = Column(Numeric(5, 4), nullable=True)
    difficulty = Column(Integer, nullable=True)
    intent = Column(String(50), nullable=True)
    trend = Column(JSONB, default=list)
    dataforseo_raw = Column(JSONB, nullable=True)

    # Rank tracking fields
    is_tracked = Column(Boolean, default=False, index=True)
    current_position = Column(Integer, nullable=True)
    previous_position = Column(Integer, nullable=True)
    best_position = Column(Integer, nullable=True)
    ranking_url = Column(Text, nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    site = relationship("Site", back_populates="keywords")
    clusters = relationship(
        "KeywordCluster",
        secondary="keyword_cluster_members",
        back_populates="keywords",
    )
    rankings = relationship(
        "KeywordRanking",
        back_populates="keyword",
        cascade="all, delete-orphan",
        order_by="desc(KeywordRanking.checked_at)",
    )

    __table_args__ = (
        UniqueConstraint("site_id", "text", "language", "country", name="uq_keyword_site_text"),
    )

    def __repr__(self) -> str:
        return f"<Keyword {self.text[:30]}... (vol: {self.search_volume})>"


class KeywordCluster(Base, BaseModel):
    """Cluster of related keywords."""
    
    __tablename__ = "keyword_clusters"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(10), default="en")
    country = Column(String(10), default="US")
    primary_keyword_id = Column(
        UUID(as_uuid=True),
        ForeignKey("keywords.id"),
        nullable=True,
    )
    mapped_url = Column(Text, nullable=True)
    is_new_page_recommended = Column(Boolean, default=False)
    
    # Relationships
    site = relationship("Site", back_populates="keyword_clusters")
    primary_keyword = relationship("Keyword", foreign_keys=[primary_keyword_id])
    keywords = relationship(
        "Keyword",
        secondary="keyword_cluster_members",
        back_populates="clusters",
    )
    content_briefs = relationship("ContentBrief", back_populates="keyword_cluster")
    
    def __repr__(self) -> str:
        return f"<KeywordCluster {self.label}>"


from sqlalchemy import Float, Table

keyword_cluster_members = Table(
    "keyword_cluster_members",
    Base.metadata,
    Column("keyword_id", UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
    Column("cluster_id", UUID(as_uuid=True), ForeignKey("keyword_clusters.id", ondelete="CASCADE"), primary_key=True),
)


class KeywordGapStatus(str, __import__("enum").Enum):
    NEW = "new"
    TARGETED = "targeted"
    IGNORED = "ignored"
    CAPTURED = "captured"


class KeywordGap(Base, BaseModel):
    """Keywords that competitors rank for but we don't."""
    
    __tablename__ = "keyword_gaps"
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword = Column(String(500), nullable=False)
    search_volume = Column(Integer, nullable=True)
    difficulty = Column(Integer, nullable=True)
    intent = Column(String(50), nullable=True)
    competitor_count = Column(Integer, default=0)
    competitors = Column(JSONB, default=list)
    priority_score = Column(Float, nullable=True)
    status = Column(String(20), default="new")
    
    # Relationships
    site = relationship("Site", back_populates="keyword_gaps")
    
    __table_args__ = (
        UniqueConstraint("site_id", "keyword", name="uq_keyword_gap_site_keyword"),
    )

    def __repr__(self) -> str:
        return f"<KeywordGap {self.keyword[:30]}... (vol: {self.search_volume})>"


class KeywordRanking(Base, BaseModel):
    """Historical ranking data for a keyword."""

    __tablename__ = "keyword_rankings"

    keyword_id = Column(
        UUID(as_uuid=True),
        ForeignKey("keywords.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=True)
    url = Column(Text, nullable=True)
    serp_features = Column(JSONB, default=dict)
    competitor_positions = Column(JSONB, default=list)
    checked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Relationships
    keyword = relationship("Keyword", back_populates="rankings")
    site = relationship("Site", back_populates="keyword_rankings")

    def __repr__(self) -> str:
        return f"<KeywordRanking keyword={self.keyword_id} pos={self.position}>"
