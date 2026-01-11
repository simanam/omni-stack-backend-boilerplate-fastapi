"""
Integration tests for project API endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.main import app
from app.models.project import Project
from app.models.user import User


@pytest.fixture
def mock_user() -> User:
    """Create a mock authenticated user."""
    return User(
        id="project_test_user",
        email="projectuser@example.com",
        full_name="Project User",
        role="user",
        is_active=True,
    )


@pytest.fixture
async def authenticated_client(client: AsyncClient, mock_user: User, session):
    """Provide client with mocked authentication."""
    session.add(mock_user)
    await session.flush()

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def sample_project(session, mock_user: User) -> Project:
    """Create a sample project for testing."""
    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        description="A test project",
        owner_id=mock_user.id,
    )
    session.add(project)
    await session.flush()
    return project


class TestProjectCRUD:
    """Integration tests for project CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_project(self, authenticated_client: AsyncClient):
        """POST /projects should create a new project."""
        response = await authenticated_client.post(
            "/api/v1/app/projects",
            json={
                "name": "New Project",
                "description": "A brand new project",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["description"] == "A brand new project"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_project_minimal(self, authenticated_client: AsyncClient):
        """POST /projects should create project with only required fields."""
        response = await authenticated_client.post(
            "/api/v1/app/projects",
            json={"name": "Minimal Project"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Project"

    @pytest.mark.asyncio
    async def test_create_project_validation_error(self, authenticated_client: AsyncClient):
        """POST /projects should return 422 for invalid data."""
        response = await authenticated_client.post(
            "/api/v1/app/projects",
            json={},  # Missing required 'name' field
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, authenticated_client: AsyncClient):
        """GET /projects should return empty list when no projects exist."""
        response = await authenticated_client.get("/api/v1/app/projects")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_projects_with_data(
        self, authenticated_client: AsyncClient, sample_project: Project
    ):
        """GET /projects should return user's projects."""
        response = await authenticated_client.get("/api/v1/app/projects")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert any(p["id"] == sample_project.id for p in data["items"])

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, authenticated_client: AsyncClient, session, mock_user: User):
        """GET /projects should support pagination."""
        # Create multiple projects
        for i in range(5):
            project = Project(
                id=str(uuid.uuid4()),
                name=f"Project {i}",
                owner_id=mock_user.id,
            )
            session.add(project)
        await session.flush()

        # Test with limit
        response = await authenticated_client.get("/api/v1/app/projects?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert "total" in data
        assert data["total"] >= 5

    @pytest.mark.asyncio
    async def test_list_projects_search(
        self, authenticated_client: AsyncClient, sample_project: Project  # noqa: ARG002
    ):
        """GET /projects should support search by name."""
        response = await authenticated_client.get("/api/v1/app/projects?search=Test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert all("Test" in p["name"] for p in data["items"])

    @pytest.mark.asyncio
    async def test_get_project(
        self, authenticated_client: AsyncClient, sample_project: Project
    ):
        """GET /projects/{id} should return project details."""
        response = await authenticated_client.get(f"/api/v1/app/projects/{sample_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_project.id
        assert data["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, authenticated_client: AsyncClient):
        """GET /projects/{id} should return 404 for nonexistent project."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(f"/api/v1/app/projects/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_unauthorized(
        self, client: AsyncClient, session, sample_project: Project  # noqa: ARG002
    ):
        """GET /projects/{id} should return 401 without auth."""
        response = await client.get(f"/api/v1/app/projects/{sample_project.id}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_project(
        self, authenticated_client: AsyncClient, sample_project: Project
    ):
        """PATCH /projects/{id} should update project."""
        response = await authenticated_client.patch(
            f"/api/v1/app/projects/{sample_project.id}",
            json={"name": "Updated Project Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, authenticated_client: AsyncClient):
        """PATCH /projects/{id} should return 404 for nonexistent project."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.patch(
            f"/api/v1/app/projects/{fake_id}",
            json={"name": "Updated"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project(
        self, authenticated_client: AsyncClient, sample_project: Project
    ):
        """DELETE /projects/{id} should soft delete project."""
        response = await authenticated_client.delete(
            f"/api/v1/app/projects/{sample_project.id}"
        )

        assert response.status_code == 204

        # Verify project is no longer accessible
        get_response = await authenticated_client.get(
            f"/api/v1/app/projects/{sample_project.id}"
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, authenticated_client: AsyncClient):
        """DELETE /projects/{id} should return 404 for nonexistent project."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.delete(f"/api/v1/app/projects/{fake_id}")

        assert response.status_code == 404


class TestProjectOwnership:
    """Tests for project ownership validation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_users_project(
        self, client: AsyncClient, session
    ):
        """Users should not access projects owned by other users."""
        # Create another user and their project
        other_user = User(
            id="other_user_456",
            email="other@example.com",
            role="user",
            is_active=True,
        )
        other_project = Project(
            id=str(uuid.uuid4()),
            name="Other's Project",
            owner_id=other_user.id,
        )
        session.add(other_user)
        session.add(other_project)
        await session.flush()

        # Create current user
        current_user = User(
            id="current_user_789",
            email="current@example.com",
            role="user",
            is_active=True,
        )
        session.add(current_user)
        await session.flush()

        async def override_get_current_user():
            return current_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            # Try to access other user's project
            response = await client.get(f"/api/v1/app/projects/{other_project.id}")

            # Should return 404 (not 403) to avoid leaking existence
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
