"""
Keyword schemas.
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, IDSchema


class KeywordDiscoverRequest(BaseSchema):
    """Keyword discovery request."""

    country: str = "US"
    language: str = "en"
    max_keywords: int = Field(default=100, ge=1, le=1000)


class KeywordExpandRequest(BaseSchema):
    """Keyword expansion request."""

    seed_keywords: list[str] = Field(min_length=1, max_length=10)
    country: str = "US"
    language: str = "en"
    max_keywords: int = Field(default=100, ge=1, le=1000)


class KeywordResponse(IDSchema):
    """Keyword response."""

    site_id: UUID
    text: str
    language: str
    country: str
    search_volume: int | None
    cpc: Decimal | None
    competition: Decimal | None
    difficulty: int | None
    intent: str | None
    trend: list[dict]
    created_at: datetime


class KeywordWithRankingResponse(KeywordResponse):
    """Keyword response with ranking data."""

    is_tracked: bool = False
    current_position: int | None = None
    previous_position: int | None = None
    best_position: int | None = None
    ranking_url: str | None = None
    last_checked_at: datetime | None = None
    position_change: int | None = None

    @classmethod
    def from_keyword(cls, keyword) -> "KeywordWithRankingResponse":
        """Create response from keyword model."""
        position_change = None
        if keyword.current_position is not None and keyword.previous_position is not None:
            position_change = keyword.previous_position - keyword.current_position

        return cls(
            id=keyword.id,
            site_id=keyword.site_id,
            text=keyword.text,
            language=keyword.language,
            country=keyword.country,
            search_volume=keyword.search_volume,
            cpc=keyword.cpc,
            competition=keyword.competition,
            difficulty=keyword.difficulty,
            intent=keyword.intent,
            trend=keyword.trend or [],
            created_at=keyword.created_at,
            is_tracked=keyword.is_tracked,
            current_position=keyword.current_position,
            previous_position=keyword.previous_position,
            best_position=keyword.best_position,
            ranking_url=keyword.ranking_url,
            last_checked_at=keyword.last_checked_at,
            position_change=position_change,
        )


class KeywordClusterResponse(IDSchema):
    """Keyword cluster response."""
    
    site_id: UUID
    label: str
    description: str | None
    language: str
    country: str
    mapped_url: str | None
    is_new_page_recommended: bool
    keywords_count: int = 0
    total_search_volume: int = 0
    created_at: datetime


class KeywordClusterDetail(KeywordClusterResponse):
    """Detailed keyword cluster with keywords."""
    
    keywords: list[KeywordResponse]
    primary_keyword: KeywordResponse | None = None


class KeywordJobResponse(BaseSchema):
    """Keyword job status response."""

    job_id: UUID
    status: str
    keywords_found: int = 0
    message: str | None = None


# Ranking schemas

class KeywordRankingResponse(IDSchema):
    """Historical ranking data response."""

    keyword_id: UUID
    site_id: UUID
    position: int | None
    url: str | None
    serp_features: dict = Field(default_factory=dict)
    competitor_positions: list[dict] = Field(default_factory=list)
    checked_at: datetime


class RankingsSummaryResponse(BaseSchema):
    """Rankings summary for a site."""

    total_tracked: int = 0
    in_top_3: int = 0
    in_top_10: int = 0
    not_ranking: int = 0
    improved: int = 0
    declined: int = 0
    average_position: float | None = None


class RankingChangesResponse(BaseSchema):
    """Keywords with ranking changes."""

    improved: list[KeywordWithRankingResponse] = Field(default_factory=list)
    declined: list[KeywordWithRankingResponse] = Field(default_factory=list)
    new_rankings: list[KeywordWithRankingResponse] = Field(default_factory=list)
    lost_rankings: list[KeywordWithRankingResponse] = Field(default_factory=list)


class SetTrackingRequest(BaseSchema):
    """Request to enable/disable keyword tracking."""

    keyword_ids: list[UUID] = Field(min_length=1, max_length=100)
    is_tracked: bool


class SetTrackingResponse(BaseSchema):
    """Response for tracking update."""

    keywords_updated: int
    is_tracked: bool


class TrackTopKeywordsRequest(BaseSchema):
    """Request to auto-track top keywords."""

    limit: int = Field(default=50, ge=1, le=200)
    min_volume: int = Field(default=100, ge=0)


class UpdateRankingsResponse(BaseSchema):
    """Response after updating rankings."""

    job_id: UUID
    status: str
    message: str
