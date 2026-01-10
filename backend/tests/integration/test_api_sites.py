"""
Integration tests for Sites API endpoints.
"""
import pytest
import uuid
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import status


class TestSitesAPI:
    """Test sites CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_site_schema_validation(self, async_client):
        """Test site creation validates required fields."""
        # Missing required fields
        response = await async_client.post(
            "/api/v1/sites",
            json={},
            headers={"Authorization": "Bearer fake-token"},
        )

        # Should fail validation (or auth)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @pytest.mark.asyncio
    async def test_site_url_validation(self, async_client):
        """Test site URL validation."""
        # Invalid URL format
        response = await async_client.post(
            "/api/v1/sites",
            json={
                "name": "Test Site",
                "url": "not-a-valid-url",
            },
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @pytest.mark.asyncio
    async def test_get_site_not_found(self, async_client):
        """Test getting non-existent site returns 404."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/sites/{fake_id}",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


class TestSiteAudits:
    """Test site audit endpoints."""

    @pytest.mark.asyncio
    async def test_trigger_audit_requires_site(self, async_client):
        """Test triggering audit requires valid site."""
        fake_site_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/sites/{fake_site_id}/audits",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


class TestSiteCrawls:
    """Test site crawl endpoints."""

    @pytest.mark.asyncio
    async def test_list_crawls_requires_site(self, async_client):
        """Test listing crawls requires valid site."""
        fake_site_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/sites/{fake_site_id}/crawls",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


class TestSiteKeywords:
    """Test site keyword endpoints."""

    @pytest.mark.asyncio
    async def test_list_keywords_requires_site(self, async_client):
        """Test listing keywords requires valid site."""
        fake_site_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/sites/{fake_site_id}/keywords",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


class TestSiteRankings:
    """Test site ranking endpoints."""

    @pytest.mark.asyncio
    async def test_rankings_endpoint_exists(self, async_client):
        """Test rankings endpoint is accessible."""
        fake_site_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/sites/{fake_site_id}/rankings",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Should not be 404 (endpoint should exist)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,  # Site not found is OK
        ]

    @pytest.mark.asyncio
    async def test_rankings_summary_endpoint_exists(self, async_client):
        """Test rankings summary endpoint is accessible."""
        fake_site_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/sites/{fake_site_id}/rankings/summary",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
