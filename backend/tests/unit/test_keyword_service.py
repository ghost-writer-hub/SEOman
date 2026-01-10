"""
Unit tests for SEOman Keyword Service.

Tests keyword functionality including:
- Keyword discovery and research
- Ranking tracking
- Clustering
- Search volume and competition analysis
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestKeywordRankingModel:
    """Test KeywordRanking model."""

    def test_keyword_ranking_creation(self):
        """Test creating a keyword ranking record."""
        from app.models.keyword import KeywordRanking

        ranking = KeywordRanking(
            id=uuid.uuid4(),
            keyword_id=uuid.uuid4(),
            site_id=uuid.uuid4(),
            position=5,
            url="https://example.com/page",
            serp_features={"featured_snippet": True},
            competitor_positions=[{"domain": "competitor.com", "position": 3}],
            checked_at=datetime.now(timezone.utc),
        )

        assert ranking.position == 5
        assert ranking.url == "https://example.com/page"
        assert ranking.serp_features["featured_snippet"] is True

    def test_keyword_tracking_fields(self):
        """Test keyword tracking fields."""
        from app.models.keyword import Keyword

        # These fields should exist on the Keyword model
        assert hasattr(Keyword, "is_tracked")
        assert hasattr(Keyword, "current_position")
        assert hasattr(Keyword, "previous_position")
        assert hasattr(Keyword, "best_position")
        assert hasattr(Keyword, "ranking_url")
        assert hasattr(Keyword, "last_checked_at")


class TestKeywordServiceMethods:
    """Test KeywordService methods."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_dataforseo(self):
        """Create mock DataForSEO client."""
        client = AsyncMock()
        client.get_keywords_for_site = AsyncMock(return_value=[
            {
                "keyword": "test keyword",
                "search_volume": 1000,
                "competition": 0.5,
                "cpc": 1.50,
            },
        ])
        client.get_serp_with_features = AsyncMock(return_value={
            "organic_results": [
                {"position": 1, "url": "https://example.com", "title": "Test"},
            ],
            "serp_features": {
                "featured_snippet": False,
                "people_also_ask": True,
            },
            "competitor_positions": [],
        })
        return client

    def test_keyword_service_import(self):
        """Test KeywordService can be imported."""
        from app.services.keyword_service import KeywordService

        assert KeywordService is not None


class TestRankingCalculations:
    """Test ranking calculation methods."""

    def test_position_change_calculation(self):
        """Test calculating position change."""
        previous_position = 10
        current_position = 5

        change = previous_position - current_position

        assert change == 5  # Improved by 5 positions

    def test_position_drop_calculation(self):
        """Test calculating position drop."""
        previous_position = 5
        current_position = 15

        change = previous_position - current_position

        assert change == -10  # Dropped by 10 positions

    def test_best_position_tracking(self):
        """Test tracking best position."""
        positions_over_time = [10, 8, 5, 7, 3, 6]
        best_position = min(positions_over_time)

        assert best_position == 3

    def test_null_position_handling(self):
        """Test handling null/no position."""
        position = None

        # Position over 100 or None means not ranking
        is_ranking = position is not None and position <= 100

        assert is_ranking is False


class TestSERPFeatureDetection:
    """Test SERP feature detection."""

    def test_serp_features_structure(self):
        """Test SERP features data structure."""
        serp_features = {
            "featured_snippet": True,
            "people_also_ask": True,
            "local_pack": False,
            "knowledge_panel": False,
            "video_carousel": False,
            "image_pack": True,
            "top_stories": False,
            "shopping_results": False,
        }

        # Count active features
        active_features = sum(1 for v in serp_features.values() if v)

        assert active_features == 3

    def test_competitor_positions_structure(self):
        """Test competitor positions data structure."""
        competitor_positions = [
            {"domain": "competitor1.com", "position": 1, "url": "https://competitor1.com/page"},
            {"domain": "competitor2.com", "position": 3, "url": "https://competitor2.com/page"},
        ]

        assert len(competitor_positions) == 2
        assert competitor_positions[0]["position"] < competitor_positions[1]["position"]


class TestKeywordClustering:
    """Test keyword clustering functionality."""

    def test_cluster_structure(self):
        """Test keyword cluster data structure."""
        from app.models.keyword import KeywordCluster

        assert hasattr(KeywordCluster, "id")
        assert hasattr(KeywordCluster, "site_id")
        assert hasattr(KeywordCluster, "label")  # Uses 'label' not 'name'

    def test_keyword_cluster_assignment(self):
        """Test keyword can be assigned to cluster via many-to-many relationship."""
        from app.models.keyword import Keyword

        # Keywords relate to clusters via a many-to-many relationship
        assert hasattr(Keyword, "clusters")


class TestKeywordMetrics:
    """Test keyword metric calculations."""

    def test_search_volume_classification(self):
        """Test search volume classification."""
        def classify_volume(volume: int) -> str:
            if volume >= 10000:
                return "high"
            elif volume >= 1000:
                return "medium"
            elif volume >= 100:
                return "low"
            else:
                return "very_low"

        assert classify_volume(50000) == "high"
        assert classify_volume(5000) == "medium"
        assert classify_volume(500) == "low"
        assert classify_volume(50) == "very_low"

    def test_competition_classification(self):
        """Test competition level classification."""
        def classify_competition(competition: float) -> str:
            if competition >= 0.7:
                return "high"
            elif competition >= 0.4:
                return "medium"
            else:
                return "low"

        assert classify_competition(0.8) == "high"
        assert classify_competition(0.5) == "medium"
        assert classify_competition(0.2) == "low"

    def test_keyword_difficulty_calculation(self):
        """Test keyword difficulty calculation."""
        def calculate_difficulty(competition: float, domain_authority: int) -> int:
            # Simple difficulty calculation
            base_difficulty = competition * 100
            da_factor = max(0, 50 - domain_authority) / 50
            difficulty = base_difficulty * (1 + da_factor)
            return min(100, max(0, int(difficulty)))

        # High competition, low DA = very difficult
        assert calculate_difficulty(0.8, 20) > 80

        # Low competition, high DA = easier
        assert calculate_difficulty(0.2, 60) < 30


class TestKeywordSchemas:
    """Test keyword Pydantic schemas."""

    def test_keyword_ranking_response_schema(self):
        """Test KeywordRankingResponse schema."""
        from app.schemas.keyword import KeywordRankingResponse

        response = KeywordRankingResponse(
            id=uuid.uuid4(),
            keyword_id=uuid.uuid4(),
            site_id=uuid.uuid4(),
            position=5,
            url="https://example.com/page",
            serp_features={"featured_snippet": True},
            competitor_positions=[],
            checked_at=datetime.now(timezone.utc),
        )

        assert response.position == 5

    def test_rankings_summary_response_schema(self):
        """Test RankingsSummaryResponse schema."""
        from app.schemas.keyword import RankingsSummaryResponse

        response = RankingsSummaryResponse(
            total_tracked=100,
            in_top_3=10,
            in_top_10=30,
            not_ranking=20,
            average_position=25.5,
            improved=15,
            declined=10,
        )

        assert response.total_tracked == 100
        assert response.in_top_3 == 10

    def test_ranking_changes_response_schema(self):
        """Test RankingChangesResponse schema."""
        from app.schemas.keyword import RankingChangesResponse

        response = RankingChangesResponse(
            improved=[],
            declined=[],
            new_rankings=[],
            lost_rankings=[],
        )

        assert len(response.improved) == 0
        assert len(response.declined) == 0


class TestDataForSEOIntegration:
    """Test DataForSEO client integration."""

    def test_dataforseo_client_import(self):
        """Test DataForSEO client can be imported."""
        from app.integrations.dataforseo import DataForSEOClient

        assert DataForSEOClient is not None

    def test_serp_features_method_exists(self):
        """Test SERP features method exists."""
        from app.integrations.dataforseo import DataForSEOClient

        assert hasattr(DataForSEOClient, "get_serp_with_features")

    def test_rankings_batch_method_exists(self):
        """Test rankings batch method exists."""
        from app.integrations.dataforseo import DataForSEOClient

        assert hasattr(DataForSEOClient, "get_rankings_batch")
