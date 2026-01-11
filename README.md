# OmniStack Backend Boilerplate

Production-ready FastAPI backend boilerplate for SaaS applications.

**Goal:** "Zero to API in 60 seconds, Zero to Production in 60 minutes"

## Quick Start

```bash
# Create virtual environment
make venv

# Activate it
source .venv/bin/activate

# Install dependencies
make install

# Start Postgres and Redis
make up

# Run API with hot reload
make dev
```

API available at `http://localhost:8000`
- Swagger UI: `/docs`
- Health check: `/api/v1/public/health`

## Tech Stack

- **Runtime:** Python 3.12+
- **Framework:** FastAPI 0.115+
- **ORM:** SQLModel (Pydantic + SQLAlchemy)
- **Database:** PostgreSQL 16+
- **Cache:** Redis 7+
- **Migrations:** Alembic
- **Background Jobs:** ARQ
- **Testing:** Pytest
- **Linting:** Ruff

## Documentation

See `CLAUDE.md` for development context and `docs/` for detailed documentation.

## License

MIT
