# Getting Started

Complete guide to set up and run OmniStack Backend.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (60 Seconds)](#quick-start-60-seconds)
3. [Environment Variables](#environment-variables)
4. [Running the Application](#running-the-application)
5. [Verifying the Setup](#verifying-the-setup)
6. [Next Steps](#next-steps)

---

## Prerequisites

### Required Software

| Software | Version | Check Command |
|----------|---------|---------------|
| Python | 3.12+ | `python --version` |
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |

### Recommended Tools

| Tool | Purpose |
|------|---------|
| [uv](https://github.com/astral-sh/uv) | Fast Python package installer |
| [HTTPie](https://httpie.io/) | CLI for HTTP requests |
| [pgAdmin](https://www.pgadmin.org/) | PostgreSQL GUI |
| [RedisInsight](https://redis.com/redis-enterprise/redis-insight/) | Redis GUI |

---

## Quick Start (60 Seconds)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/backend-boilerplate-fastapi.git
cd backend-boilerplate-fastapi

# 2. Create virtual environment
make venv

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Install dependencies
make install

# 5. Copy environment file
cp .env.example .env

# 6. Start Docker services (PostgreSQL + Redis)
make up

# 7. Run the API server
make dev
```

**That's it!** Your API is running at `http://localhost:8000`

- Swagger UI: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/public/health

---

## Environment Variables

### Minimal Setup

Create a `.env` file with these essential variables:

```bash
# .env

# Core (REQUIRED)
SECRET_KEY="your-secret-key-at-least-32-characters-long"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/omnistack"

# Optional but recommended
REDIS_URL="redis://localhost:6379/0"
ENVIRONMENT="local"
DEBUG="true"
```

### Full Configuration

<details>
<summary>Click to expand full environment variables</summary>

```bash
# ============================================
# CORE SETTINGS
# ============================================
PROJECT_NAME="My SaaS API"
ENVIRONMENT="local"                    # local | staging | production
DEBUG="true"                           # Enable debug mode
LOG_LEVEL="INFO"                       # DEBUG | INFO | WARNING | ERROR
SECRET_KEY="your-secret-key-minimum-32-characters"

# ============================================
# DATABASE
# ============================================
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/omnistack"
DB_POOL_SIZE="10"                      # Connection pool size
DB_POOL_RECYCLE="3600"                 # Recycle connections (seconds)
DB_USE_NULL_POOL="false"               # true for serverless (Neon, Supabase)

# ============================================
# REDIS / CACHE
# ============================================
REDIS_URL="redis://localhost:6379/0"

# ============================================
# AUTHENTICATION
# ============================================
AUTH_PROVIDER="supabase"               # supabase | clerk | custom

# Supabase Auth
SUPABASE_PROJECT_URL="https://xxx.supabase.co"
SUPABASE_JWT_SECRET=""                 # Only for legacy HS256

# Clerk Auth
CLERK_ISSUER_URL="https://xxx.clerk.accounts.dev"
CLERK_SECRET_KEY=""

# ============================================
# AI PROVIDERS (Optional)
# ============================================
AI_DEFAULT_PROVIDER="openai"           # openai | anthropic | gemini
AI_DEFAULT_MODEL="gpt-4o"
OPENAI_API_KEY=""
ANTHROPIC_API_KEY=""
GOOGLE_API_KEY=""

# ============================================
# EMAIL (Optional)
# ============================================
EMAIL_PROVIDER="console"               # resend | sendgrid | console
EMAIL_FROM_ADDRESS="hello@example.com"
EMAIL_FROM_NAME="My App"
RESEND_API_KEY=""
SENDGRID_API_KEY=""

# ============================================
# STORAGE (Optional)
# ============================================
STORAGE_PROVIDER="local"               # s3 | r2 | cloudinary | local
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_REGION="us-east-1"
AWS_S3_BUCKET=""

# ============================================
# STRIPE (Optional)
# ============================================
STRIPE_SECRET_KEY=""
STRIPE_WEBHOOK_SECRET=""
STRIPE_PRICE_ID_MONTHLY=""
STRIPE_PRICE_ID_YEARLY=""

# ============================================
# OBSERVABILITY (Optional)
# ============================================
SENTRY_DSN=""
SENTRY_TRACES_SAMPLE_RATE="0.1"

# ============================================
# RATE LIMITING
# ============================================
RATE_LIMIT_DEFAULT="60/minute"
RATE_LIMIT_AI="10/minute"
RATE_LIMIT_AUTH="5/minute"

# ============================================
# CONTACT FORM (Optional)
# ============================================
CONTACT_REQUIRE_SUBJECT="false"        # Make subject required
CONTACT_REQUIRE_PHONE="false"          # Make phone required
CONTACT_SEND_CONFIRMATION="true"       # Send confirmation to sender
CONTACT_WEBHOOK_URL=""                 # CRM webhook URL
CONTACT_RATE_LIMIT="5/hour"            # Rate limit per IP
ADMIN_EMAIL=""                         # Admin notification email

# ============================================
# CORS
# ============================================
BACKEND_CORS_ORIGINS='["http://localhost:3000"]'
```

</details>

### Environment-Specific Files

| File | Purpose | Git Status |
|------|---------|------------|
| `.env.example` | Template with all variables | Committed |
| `.env` | Local development | Ignored |
| `.env.test` | Test environment | Ignored |
| `.env.production` | Production (reference) | Ignored |

---

## Running the Application

### Development Mode (Recommended)

```bash
# Start database and cache
make up

# Run API with hot reload
make dev

# API available at http://localhost:8000
```

### Using Docker

```bash
# Build and run everything in Docker
docker compose -f docker/docker-compose.yml up

# Or build production image
docker build -f docker/Dockerfile -t omnistack-api .
docker run -p 8000:8000 --env-file .env omnistack-api
```

### Background Worker

For background jobs (emails, reports, etc.):

```bash
# Terminal 1: API server
make dev

# Terminal 2: Background worker
make worker
```

---

## Verifying the Setup

### 1. Health Check

```bash
curl http://localhost:8000/api/v1/public/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-10T12:00:00Z"
}
```

### 2. Readiness Check (with DB/Redis)

```bash
curl http://localhost:8000/api/v1/public/health/ready
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-10T12:00:00Z",
  "components": {
    "database": { "status": "healthy" },
    "cache": { "status": "healthy" }
  }
}
```

### 3. Swagger UI

Open http://localhost:8000/docs in your browser to see the interactive API documentation.

### 4. Run Tests

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_health.py -v
```

### 5. Lint Check

```bash
make lint
```

---

## Make Commands Reference

| Command | Description |
|---------|-------------|
| `make venv` | Create Python virtual environment |
| `make install` | Install all dependencies |
| `make dev` | Run API with hot reload |
| `make up` | Start Docker services (DB + Redis) |
| `make down` | Stop Docker services |
| `make test` | Run test suite |
| `make lint` | Run linter (Ruff) |
| `make worker` | Start background worker |
| `make worker-dev` | Start worker with auto-reload |
| `make migrate msg="description"` | Generate and run migration |

---

## Project Structure Overview

```
backend-boilerplate-fastapi/
├── app/                      # Application code
│   ├── main.py               # FastAPI app entry point
│   ├── api/                  # HTTP endpoints
│   │   ├── deps.py           # Dependencies (auth, db session)
│   │   └── v1/               # API version 1
│   │       ├── public/       # No auth required
│   │       ├── app/          # Auth required
│   │       └── admin/        # Admin only
│   ├── core/                 # Core utilities
│   │   ├── config.py         # Environment configuration
│   │   ├── db.py             # Database setup
│   │   ├── security.py       # JWT verification
│   │   └── exceptions.py     # Custom exceptions
│   ├── models/               # Database models (SQLModel)
│   ├── schemas/              # Request/response schemas
│   ├── business/             # Business logic services
│   ├── services/             # External service adapters
│   │   ├── ai/               # AI providers
│   │   ├── email/            # Email providers
│   │   ├── storage/          # Storage providers
│   │   └── payments/         # Payment providers
│   └── jobs/                 # Background tasks
├── migrations/               # Alembic migrations
├── tests/                    # Test suite
├── docker/                   # Docker configuration
├── documentation/            # Documentation (you are here)
└── .env.example              # Environment template
```

---

## Database Setup

### Run Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# View migration history
alembic history
```

### Create New Migration

```bash
# Auto-generate migration from model changes
make migrate msg="add user profile fields"

# Or manually
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Reset Database (Development)

```bash
# Warning: This deletes all data
make down
docker volume rm backend-boilerplate-fastapi_postgres_data
make up
alembic upgrade head
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

### Local PostgreSQL Conflict

If you have local PostgreSQL running (Homebrew), it conflicts with Docker:

```bash
# Stop local PostgreSQL
brew services stop postgresql@17  # or your version

# Then start Docker services
make up
```

### Module Not Found

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -e ".[dev]"
```

### Database Connection Failed

1. Check Docker is running: `docker ps`
2. Check DATABASE_URL in `.env`
3. Try reconnecting: `make down && make up`

### Redis Connection Failed

Redis is optional. The app works without it (rate limiting falls back to memory).

To enable Redis:
```bash
# Make sure REDIS_URL is set in .env
REDIS_URL="redis://localhost:6379/0"

# Check Redis is running
docker ps | grep redis
```

---

## Observability Setup (Optional)

### Distributed Tracing with OpenTelemetry

Enable distributed tracing to track requests across services:

```bash
# Add to .env
OTEL_ENABLED=true
OTEL_SERVICE_NAME="my-api"
OTEL_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
```

**Quick Start with Jaeger:**

```bash
# Start Jaeger (all-in-one)
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# View traces at http://localhost:16686
```

**Install tracing dependencies:**

```bash
pip install -e ".[tracing]"
```

For development, use console exporter to see traces in terminal:

```bash
OTEL_ENABLED=true
OTEL_EXPORTER=console
```

### Error Tracking with Sentry

```bash
# Add to .env
SENTRY_DSN="https://xxx@sentry.io/xxx"
SENTRY_TRACES_SAMPLE_RATE=0.1  # Sample 10% of requests
```

### Prometheus Metrics

Metrics are available at `/api/v1/public/metrics` for Prometheus scraping.

---

## Next Steps

1. **Configure Authentication**
   - Set up [Supabase](https://supabase.com) or [Clerk](https://clerk.dev)
   - Update `AUTH_PROVIDER` and related env vars

2. **Read the Architecture Guide**
   - [Architecture Documentation](./ARCHITECTURE.md)
   - Learn naming conventions and patterns

3. **Explore the API**
   - [API Reference](./API-REFERENCE.md)
   - Test endpoints in Swagger UI

4. **Customize for Your Needs**
   - [Modular Guide](./MODULAR-GUIDE.md)
   - Remove components you don't need

5. **Frontend Integration**
   - [Frontend Integration Guide](./FRONTEND-INTEGRATION.md)
   - TypeScript types and examples

---

## Getting Help

- Check the [API Reference](./API-REFERENCE.md) for endpoint details
- Review [Architecture](./ARCHITECTURE.md) for code patterns
- Open an issue on GitHub for bugs
- Read the inline code documentation
