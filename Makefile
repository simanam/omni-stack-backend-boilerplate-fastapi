.PHONY: help dev up down logs migrate test lint format clean install shell worker worker-dev venv

# Python - use python3.12 if available, otherwise python3
PYTHON := $(shell which python3.12 2>/dev/null || which python3)

# Default target
help:
	@echo "OmniStack Backend - Available Commands"
	@echo "======================================="
	@echo ""
	@echo "Development:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Start API with hot reload (local)"
	@echo "  make up         - Start Docker services (DB, Redis)"
	@echo "  make down       - Stop Docker services"
	@echo "  make logs       - View Docker logs"
	@echo "  make shell      - Open Python shell"
	@echo ""
	@echo "Database:"
	@echo "  make migrate    - Generate and apply migrations"
	@echo "  make migrate-up - Apply pending migrations"
	@echo "  make migrate-down - Rollback last migration"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test       - Run test suite"
	@echo "  make lint       - Run linter (ruff check)"
	@echo "  make format     - Format code (ruff format)"
	@echo ""
	@echo "Background Jobs:"
	@echo "  make worker     - Start ARQ worker"
	@echo "  make worker-dev - Start ARQ worker with auto-reload"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean      - Remove cache files"
	@echo "  make venv       - Create virtual environment"

# Create virtual environment
venv:
	$(PYTHON) -m venv .venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source .venv/bin/activate"

# Install dependencies (run after activating venv)
install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

# Start API locally with hot reload
dev:
	uvicorn app.main:app --reload --port 8000

# Start Docker services (Postgres, Redis)
up:
	docker compose -f docker/docker-compose.yml up -d db redis

# Stop Docker services
down:
	docker compose -f docker/docker-compose.yml down

# View Docker logs
logs:
	docker compose -f docker/docker-compose.yml logs -f

# Start all services including API in Docker
up-all:
	docker compose -f docker/docker-compose.yml up -d

# Generate and apply migrations
migrate:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg" && \
	alembic upgrade head

# Apply pending migrations
migrate-up:
	alembic upgrade head

# Rollback last migration
migrate-down:
	alembic downgrade -1

# Run tests
test:
	pytest tests/ -v --cov=app --cov-report=term-missing

# Run linter
lint:
	ruff check app/ tests/

# Format code
format:
	ruff format app/ tests/
	ruff check app/ tests/ --fix

# Start ARQ background worker
worker:
	arq app.jobs.worker.WorkerSettings

# Start ARQ worker with watchfiles for development (auto-reload)
worker-dev:
	watchfiles --filter python 'arq app.jobs.worker.WorkerSettings' app/

# Open Python shell with app context
shell:
	python -c "import asyncio; from app.main import app; print('App loaded. Use asyncio.run() for async calls.')"
	python

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f test.db 2>/dev/null || true
