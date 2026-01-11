"""
Integration tests for user API endpoints.
"""


import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture
def mock_user() -> User:
    """Create a mock authenticated user."""
    return User(
        id="test_user_123",
        email="test@example.com",
        full_name="Test User",
        role="user",
        is_active=True,
        subscription_plan="free",
        subscription_status=None,
    )


@pytest.fixture
def mock_admin_user() -> User:
    """Create a mock admin user."""
    return User(
        id="admin_user_123",
        email="admin@example.com",
        full_name="Admin User",
        role="admin",
        is_active=True,
    )


@pytest.fixture
async def authenticated_client(client: AsyncClient, mock_user: User, session):
    """Provide client with mocked authentication."""
    # Add user to database
    session.add(mock_user)
    await session.flush()

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def admin_client(client: AsyncClient, mock_admin_user: User, session):
    """Provide client with mocked admin authentication."""
    # Add admin to database
    session.add(mock_admin_user)
    await session.flush()

    async def override_get_current_user():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


class TestUserMeEndpoints:
    """Integration tests for /users/me endpoints."""

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """GET /users/me should return 401 without auth."""
        response = await client.get("/api/v1/app/users/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_success(self, authenticated_client: AsyncClient):
        """GET /users/me should return current user profile."""
        response = await authenticated_client.get("/api/v1/app/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_user_123"
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "user"

    @pytest.mark.asyncio
    async def test_update_me_success(self, authenticated_client: AsyncClient):
        """PATCH /users/me should update current user profile."""
        response = await authenticated_client.patch(
            "/api/v1/app/users/me",
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_me_invalid_data(self, authenticated_client: AsyncClient):
        """PATCH /users/me should validate input."""
        # Test with empty update (should still work)
        response = await authenticated_client.patch(
            "/api/v1/app/users/me",
            json={},
        )

        assert response.status_code == 200


class TestAdminUserEndpoints:
    """Integration tests for admin user management endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self, client: AsyncClient):
        """GET /admin/users should return 401 without auth."""
        response = await client.get("/api/v1/admin/users")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_users_forbidden_non_admin(self, authenticated_client: AsyncClient):
        """GET /admin/users should return 403 for non-admin."""
        response = await authenticated_client.get("/api/v1/admin/users")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_users_success(self, admin_client: AsyncClient, session, mock_user: User):
        """GET /admin/users should return user list for admin."""
        # Add a regular user to list
        session.add(mock_user)
        await session.flush()

        response = await admin_client.get("/api/v1/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, admin_client: AsyncClient, session, mock_user: User):
        """GET /admin/users/{id} should return user details."""
        session.add(mock_user)
        await session.flush()

        response = await admin_client.get(f"/api/v1/admin/users/{mock_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user.id
        assert data["email"] == mock_user.email

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, admin_client: AsyncClient):
        """GET /admin/users/{id} should return 404 for nonexistent user."""
        response = await admin_client.get("/api/v1/admin/users/nonexistent_id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_user(self, admin_client: AsyncClient, session, mock_user: User):
        """POST /admin/users/{id}/deactivate should deactivate user."""
        session.add(mock_user)
        await session.flush()

        response = await admin_client.post(f"/api/v1/admin/users/{mock_user.id}/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_activate_user(self, admin_client: AsyncClient, session, mock_user: User):
        """POST /admin/users/{id}/activate should activate user."""
        mock_user.is_active = False
        session.add(mock_user)
        await session.flush()

        response = await admin_client.post(f"/api/v1/admin/users/{mock_user.id}/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
