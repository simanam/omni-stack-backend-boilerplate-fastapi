# Deployment Guide

This guide covers deploying OmniStack Backend to various cloud platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Railway Deployment](#railway-deployment)
4. [Render Deployment](#render-deployment)
5. [Fly.io Deployment](#flyio-deployment)
6. [Docker Deployment](#docker-deployment)
7. [Database Migrations](#database-migrations)
8. [Rollback Procedures](#rollback-procedures)
9. [Scaling Guidelines](#scaling-guidelines)
10. [Monitoring & Observability](#monitoring--observability)

---

## Prerequisites

Before deploying, ensure you have:

- A GitHub repository with the codebase
- Database (PostgreSQL 16+) provisioned
- Redis instance for caching and background jobs
- Required API keys for external services

---

## Environment Variables

### Required Variables

```bash
# Core
SECRET_KEY="your-secret-key-minimum-32-characters"
DATABASE_URL="postgresql+asyncpg://user:password@host:5432/dbname"
ENVIRONMENT="production"

# Authentication (choose one)
AUTH_PROVIDER="supabase"  # or "clerk"
SUPABASE_PROJECT_URL="https://xxx.supabase.co"
# OR
CLERK_ISSUER_URL="https://xxx.clerk.accounts.dev"
```

### Optional Variables

```bash
# Redis (recommended)
REDIS_URL="redis://user:password@host:6379/0"

# Observability
SENTRY_DSN="https://xxx@sentry.io/xxx"
SENTRY_TRACES_SAMPLE_RATE="0.1"

# AI Services
OPENAI_API_KEY="sk-xxx"
ANTHROPIC_API_KEY="sk-ant-xxx"

# Email
EMAIL_PROVIDER="resend"
RESEND_API_KEY="re_xxx"

# Payments
STRIPE_SECRET_KEY="sk_live_xxx"
STRIPE_WEBHOOK_SECRET="whsec_xxx"
```

### Secret Management Best Practices

1. **Never commit secrets** - Use environment variables or secret managers
2. **Rotate secrets regularly** - Especially API keys and tokens
3. **Use different secrets per environment** - staging vs production
4. **Audit secret access** - Track who has access to production secrets

---

## Railway Deployment

Railway provides simple deployments with automatic SSL and scaling.

### Quick Start

1. **Connect your GitHub repo** to Railway
2. Railway will auto-detect `railway.toml` configuration
3. **Set environment variables** in Railway dashboard
4. **Add PostgreSQL** and **Redis** services
5. Deploy!

### Configuration

The `railway.toml` file configures the deployment:

```toml
[build]
builder = "dockerfile"
dockerfilePath = "docker/Dockerfile"

[deploy]
healthcheckPath = "/api/v1/public/health"
healthcheckTimeout = 30
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Adding Services

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis
```

### Deploy Commands

```bash
# Deploy from CLI
railway up

# View logs
railway logs

# Open shell
railway shell
```

---

## Render Deployment

Render uses the `render.yaml` blueprint for infrastructure as code.

### Quick Start

1. **Create a Render account** and connect your GitHub repo
2. Render will auto-detect `render.yaml`
3. **Click "New Blueprint Instance"**
4. Configure any manual environment variables
5. Deploy!

### Blueprint Structure

The `render.yaml` defines:

- **Web Service** - The FastAPI application
- **Worker Service** - Background job processor
- **PostgreSQL Database** - Primary data store
- **Redis Instance** - Cache and job queue

### Manual Deployment

```bash
# Using Render API
curl -X POST "https://api.render.com/v1/services/YOUR_SERVICE_ID/deploys" \
  -H "Authorization: Bearer YOUR_RENDER_API_KEY"
```

---

## Fly.io Deployment

Fly.io offers edge deployments with global distribution.

### Quick Start

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch (first time)
fly launch --config fly.toml

# Deploy updates
fly deploy
```

### Configuration

The `fly.toml` configures:

```toml
app = "omnistack-api"
primary_region = "sjc"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
```

### Secrets Management

```bash
# Set secrets
fly secrets set SECRET_KEY="your-secret-key" DATABASE_URL="postgres://..."

# List secrets
fly secrets list

# Import from .env file
fly secrets import < .env.production
```

### Scaling

```bash
# Scale to 2 machines
fly scale count 2

# Scale machine size
fly scale vm shared-cpu-2x

# View current scale
fly scale show
```

---

## Docker Deployment

For self-hosted or Kubernetes deployments.

### Build Production Image

```bash
# Build
docker build -f docker/Dockerfile -t omnistack-api:latest .

# Run
docker run -d \
  -p 8000:8000 \
  -e SECRET_KEY="your-secret-key" \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  omnistack-api:latest
```

### Docker Compose (Production)

```yaml
version: "3.9"

services:
  api:
    image: omnistack-api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/public/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    image: omnistack-api:latest
    command: arq app.jobs.worker.WorkerSettings
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - db
      - redis
```

---

## Database Migrations

### Running Migrations

```bash
# Local/Development
alembic upgrade head

# Production (via script)
python scripts/migrate_production.py

# Check current revision
alembic current

# View migration history
alembic history
```

### Migration Best Practices

1. **Test migrations locally first** with production data copy
2. **Use backward-compatible migrations** for zero-downtime deploys
3. **Create rollback migrations** for each forward migration
4. **Run migrations before deploying new code**

### Zero-Downtime Migration Pattern

1. Add new column as nullable
2. Deploy code that writes to both old and new columns
3. Backfill existing data
4. Deploy code that only uses new column
5. Drop old column

---

## Rollback Procedures

### Code Rollback

```bash
# Railway
railway up --commit <previous-commit-sha>

# Render
# Use Render dashboard to select previous deployment

# Fly.io
fly deploy --image ghcr.io/your-org/omnistack-api:previous-tag

# Docker
docker pull omnistack-api:previous-tag
docker stop api && docker run -d --name api omnistack-api:previous-tag
```

### Database Rollback

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision-id>

# Rollback all
alembic downgrade base
```

### Emergency Procedures

1. **Identify the issue** - Check logs and metrics
2. **Stop bleeding** - Roll back to last known good version
3. **Communicate** - Notify stakeholders
4. **Investigate** - Root cause analysis
5. **Fix and test** - Fix the issue in a safe environment
6. **Deploy** - Roll forward with the fix

---

## Scaling Guidelines

### Horizontal Scaling

| Metric | Action |
|--------|--------|
| CPU > 70% sustained | Add more instances |
| Memory > 80% | Add more instances or increase instance size |
| Response time > 500ms | Add instances or optimize code |
| Queue depth growing | Add more workers |

### Recommended Starting Configuration

| Environment | API Instances | Worker Instances | DB Size |
|-------------|---------------|------------------|---------|
| Development | 1 | 1 | 1 GB |
| Staging | 1-2 | 1 | 5 GB |
| Production | 2-4 | 2 | 20+ GB |

### Database Connection Pooling

```python
# For serverless databases (Neon, Supabase pooler)
DB_POOL_SIZE=5
DB_USE_NULL_POOL=true

# For dedicated databases
DB_POOL_SIZE=20
DB_USE_NULL_POOL=false
```

---

## Monitoring & Observability

### Sentry Setup

1. Create a Sentry project at https://sentry.io
2. Get your DSN from Project Settings > Client Keys
3. Set environment variables:

```bash
SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx"
SENTRY_TRACES_SAMPLE_RATE="0.1"  # 10% of requests
```

### Prometheus Metrics

Access metrics at `/api/v1/public/metrics`:

```bash
# Key metrics to monitor
http_requests_total              # Total requests by endpoint
http_request_duration_seconds    # Request latency
db_queries_total                 # Database query count
background_jobs_total            # Job execution count
```

### Log Aggregation

Logs are output in JSON format in production:

```json
{
  "timestamp": "2026-01-10T12:00:00Z",
  "level": "INFO",
  "message": "Request processed",
  "service": "omnistack-api",
  "environment": "production",
  "request_id": "abc123"
}
```

Recommended log aggregation services:
- Datadog
- Papertrail
- LogDNA
- AWS CloudWatch

### Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/api/v1/public/health` | Basic liveness check |
| `/api/v1/public/health/ready` | Readiness check (includes DB/Redis) |
| `/api/v1/public/metrics` | Prometheus metrics |

### Alerting Recommendations

| Condition | Severity | Action |
|-----------|----------|--------|
| Health check failing | Critical | Page on-call |
| Error rate > 1% | High | Investigate immediately |
| Latency P95 > 1s | Medium | Investigate |
| Queue depth > 1000 | Medium | Scale workers |

---

## CI/CD Pipeline

The GitHub Actions workflows handle:

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Linting (Ruff)
   - Type checking (mypy)
   - Unit tests
   - Integration tests
   - Docker build

2. **Deploy Pipeline** (`.github/workflows/deploy.yml`)
   - Build and push to container registry
   - Deploy to staging
   - Run smoke tests
   - Deploy to production

3. **Security Scan** (`.github/workflows/security.yml`)
   - Dependency vulnerability scan
   - Code security scan (Bandit, Semgrep)
   - Container scan (Trivy)
   - Secrets detection

### Required GitHub Secrets

```
RAILWAY_TOKEN          # Railway API token
RENDER_API_KEY         # Render API key
FLY_API_TOKEN          # Fly.io API token
SENTRY_AUTH_TOKEN      # Sentry release tracking
SLACK_WEBHOOK_URL      # Deployment notifications
```

---

## Troubleshooting

### Common Issues

**Database connection errors**
```bash
# Check connection string format
postgresql+asyncpg://user:password@host:5432/dbname

# For SSL connections
?sslmode=require
```

**Container health check failing**
```bash
# Check if the app is running
curl http://localhost:8000/api/v1/public/health

# Check container logs
docker logs <container-id>
```

**Migrations failing**
```bash
# Check current state
alembic current

# Check for pending migrations
alembic heads

# Generate new migration
alembic revision --autogenerate -m "description"
```

### Getting Help

- Check logs first: `railway logs` / `fly logs` / `render logs`
- Review metrics in Sentry or your monitoring tool
- Check the GitHub Actions workflow runs
- Review the technical PRD in `docs/omnistack-technical-prd.md`

---

*Last Updated: January 2026*
