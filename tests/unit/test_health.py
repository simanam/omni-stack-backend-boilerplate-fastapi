"""
Tests for health check endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient):
        """Test basic liveness probe."""
        response = await client.get("/api/v1/public/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_ready_returns_status(self, client: AsyncClient):
        """Test readiness probe returns component status."""
        response = await client.get("/api/v1/public/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert "database" in data["components"]
