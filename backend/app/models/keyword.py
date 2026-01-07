"""
Keyword models for SEO keyword research.
"""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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
    
    # Relationships
    site = relationship("Site", back_populates="keywords")
    clusters = relationship(
        "KeywordCluster",
        secondary="keyword_cluster_members",
        back_populates="keywords",
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
    is_new_page_recommended = Column(default=False)
    
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


# Association table for keyword-cluster many-to-many
from sqlalchemy import Table

keyword_cluster_members = Table(
    "keyword_cluster_members",
    Base.metadata,
    Column("keyword_id", UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
    Column("cluster_id", UUID(as_uuid=True), ForeignKey("keyword_clusters.id", ondelete="CASCADE"), primary_key=True),
)
