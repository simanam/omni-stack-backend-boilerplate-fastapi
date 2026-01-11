# Contributing Guide

Thank you for your interest in contributing to OmniStack Backend! This guide will help you get started.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Code Style](#code-style)
6. [Testing](#testing)
7. [Pull Request Process](#pull-request-process)
8. [Issue Guidelines](#issue-guidelines)

---

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to learn and build great software together.

---

## Getting Started

### Types of Contributions

| Type | Description | Label |
|------|-------------|-------|
| Bug Fix | Fix a reported bug | `bug` |
| Feature | Add new functionality | `enhancement` |
| Documentation | Improve docs | `documentation` |
| Refactor | Code improvement without changing behavior | `refactor` |
| Test | Add or improve tests | `testing` |

### First-Time Contributors

Look for issues labeled `good first issue` - these are specifically designed for newcomers.

---

## Development Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### Setup Steps

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/backend-boilerplate-fastapi.git
cd backend-boilerplate-fastapi

# 3. Add upstream remote
git remote add upstream https://github.com/omnistack/backend-boilerplate-fastapi.git

# 4. Create virtual environment
make venv
source .venv/bin/activate

# 5. Install all dependencies (including dev)
pip install -e ".[all]"

# 6. Copy environment file
cp .env.example .env

# 7. Start services
make up

# 8. Run tests to verify setup
make test
make lint
```

### Keep Your Fork Updated

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

---

## Making Changes

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/description` | `feature/add-webhook-retry` |
| Bug fix | `fix/description` | `fix/rate-limit-header` |
| Docs | `docs/description` | `docs/update-api-reference` |
| Refactor | `refactor/description` | `refactor/simplify-crud-base` |

### Workflow

```bash
# 1. Create a new branch
git checkout -b feature/my-feature

# 2. Make your changes
# ... edit files ...

# 3. Run tests
make test

# 4. Run linter
make lint

# 5. Commit your changes
git add .
git commit -m "feat: add webhook retry mechanism"

# 6. Push to your fork
git push origin feature/my-feature

# 7. Open a Pull Request on GitHub
```

---

## Code Style

### Python Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
# Check for issues
make lint

# Or run directly
ruff check app/ tests/
ruff format app/ tests/ --check
```

### Style Rules

| Rule | Description |
|------|-------------|
| Line length | 100 characters max |
| Quotes | Double quotes `"` |
| Imports | Sorted by `isort` (via Ruff) |
| Type hints | Required for all public functions |
| Docstrings | Required for public classes and functions |

### Examples

**Good:**
```python
async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> User | None:
    """
    Get a user by their email address.

    Args:
        session: Database session.
        email: Email to search for.

    Returns:
        User if found, None otherwise.
    """
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()
```

**Bad:**
```python
async def get_user_by_email(session, email):  # Missing type hints
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `user_service.py` |
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user_by_id` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Variables | snake_case | `user_count` |

### Import Order

```python
# 1. Standard library
import json
from datetime import datetime

# 2. Third-party
from fastapi import APIRouter, HTTPException
from sqlmodel import select

# 3. Local imports
from app.core.config import settings
from app.models.user import User
```

---

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific file
pytest tests/unit/test_user_service.py -v

# Run specific test
pytest tests/unit/test_user_service.py::test_get_user -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests (no external deps)
│   ├── test_health.py
│   ├── test_user_service.py
│   └── ...
├── integration/          # Integration tests (with DB)
│   ├── test_api_health.py
│   ├── test_api_users.py
│   └── ...
└── load/                 # Load tests (Locust)
    └── locustfile.py
```

### Writing Tests

**Unit Test Example:**

```python
# tests/unit/test_project_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.business.project_service import project_service
from app.models.project import Project
from app.schemas.project import ProjectCreate


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_project():
    """Create a sample project."""
    return Project(
        id="test-id",
        name="Test Project",
        description="A test project",
        owner_id="user-123",
    )


class TestProjectService:
    async def test_create_with_owner(self, mock_session):
        """Test creating a project with owner."""
        # Arrange
        create_data = ProjectCreate(name="New Project", description="Description")
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await project_service.create_with_owner(
            mock_session,
            obj_in=create_data,
            owner_id="user-123",
        )

        # Assert
        assert result.name == "New Project"
        assert result.owner_id == "user-123"
        mock_session.add.assert_called_once()


    async def test_get_not_found(self, mock_session):
        """Test getting a non-existent project."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await project_service.get(mock_session, id="non-existent")

        # Assert
        assert result is None
```

**Integration Test Example:**

```python
# tests/integration/test_api_projects.py

import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Get authentication headers with a valid token."""
    # Create test token
    return {"Authorization": "Bearer test-token"}


class TestProjectsAPI:
    async def test_create_project(self, client: AsyncClient, auth_headers: dict):
        """Test creating a new project."""
        response = await client.post(
            "/api/v1/app/projects",
            json={"name": "Test Project", "description": "A test"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert "id" in data


    async def test_list_projects_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing projects with pagination."""
        # Create multiple projects first
        for i in range(25):
            await client.post(
                "/api/v1/app/projects",
                json={"name": f"Project {i}"},
                headers=auth_headers,
            )

        # Test first page
        response = await client.get(
            "/api/v1/app/projects",
            params={"skip": 0, "limit": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] >= 25
        assert data["skip"] == 0
        assert data["limit"] == 10


    async def test_create_project_unauthenticated(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.post(
            "/api/v1/app/projects",
            json={"name": "Test"},
        )

        assert response.status_code == 401
```

### Test Coverage

Aim for at least 80% code coverage. Check coverage:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally (`make test`)
- [ ] Linter passes (`make lint`)
- [ ] Code follows style guidelines
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |

**Examples:**

```
feat(auth): add support for Clerk authentication

fix(billing): correct invoice amount calculation

docs(api): update billing endpoint documentation

refactor(crud): simplify generic CRUD base class

test(projects): add integration tests for project search
```

### PR Description Template

```markdown
## Summary
Brief description of changes.

## Changes
- Added X
- Fixed Y
- Updated Z

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manually tested

## Related Issues
Fixes #123
```

### Review Process

1. **Automated checks** run (tests, lint)
2. **Code review** by maintainer
3. **Address feedback** if requested
4. **Approval** and merge

---

## Issue Guidelines

### Bug Reports

Use the bug report template:

```markdown
**Description**
Clear description of the bug.

**Steps to Reproduce**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**
What should happen.

**Actual Behavior**
What actually happens.

**Environment**
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.12.0]
- Package version: [e.g., 0.1.0]

**Additional Context**
Any other relevant information.
```

### Feature Requests

Use the feature request template:

```markdown
**Problem**
What problem does this solve?

**Proposed Solution**
How should it work?

**Alternatives Considered**
Other approaches you've thought of.

**Additional Context**
Any other relevant information.
```

---

## Development Tips

### Debugging

```python
# Use Python debugger
import pdb; pdb.set_trace()

# Or better, use ipdb
import ipdb; ipdb.set_trace()

# Print SQL queries
# Add to .env: SQLALCHEMY_ECHO=true
```

### Database Migrations

```bash
# Create a new migration
make migrate msg="add new field to users"

# Or manually
alembic revision --autogenerate -m "description"
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

### Local Testing with Different Configs

```bash
# Test with different auth provider
AUTH_PROVIDER=clerk make test

# Test without Redis
REDIS_URL= make test
```

### VS Code Settings

Recommended `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

---

## Questions?

- Open a [GitHub Discussion](https://github.com/omnistack/backend-boilerplate-fastapi/discussions)
- Check existing issues and PRs
- Read the documentation

Thank you for contributing!
