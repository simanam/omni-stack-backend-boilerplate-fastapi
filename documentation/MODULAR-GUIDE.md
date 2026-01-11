# Modular Guide: Pick & Choose Components

This boilerplate is designed like Lego blocks. You can easily pick and choose only what you need.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Map](#component-map)
3. [Common Configurations](#common-configurations)
4. [Removal Instructions](#removal-instructions)
5. [Minimal Setups](#minimal-setups)
6. [Adding Components Back](#adding-components-back)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CORE (Required)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  app/core/    │  app/api/deps.py  │  app/models/base.py        │   │
│  │  config.py    │  DBSession        │  BaseModel                  │   │
│  │  db.py        │  CurrentUser      │  SoftDeleteMixin            │   │
│  │  security.py  │  CurrentUserId    │                             │   │
│  │  exceptions.py│                   │                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│   AUTH MODULE     │   │   CRUD PATTERNS   │   │  MIDDLEWARE       │
│   (Required)      │   │   (Required)      │   │  (Recommended)    │
│                   │   │                   │   │                   │
│ - User model      │   │ - crud_base.py    │   │ - Rate limiting   │
│ - JWT verify      │   │ - Generic CRUD    │   │ - Request ID      │
│ - User sync       │   │ - Pagination      │   │ - Logging         │
└───────────────────┘   └───────────────────┘   │ - Security headers│
                                                └───────────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    │                               │                               │
    ▼                               ▼                               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  AI MODULE  │ │EMAIL MODULE │ │STORAGE MOD. │ │PAYMENT MOD. │ │  JOBS MOD.  │
│ (Optional)  │ │ (Optional)  │ │ (Optional)  │ │ (Optional)  │ │ (Optional)  │
│             │ │             │ │             │ │             │ │             │
│ - OpenAI    │ │ - Resend    │ │ - S3        │ │ - Stripe    │ │ - ARQ       │
│ - Anthropic │ │ - SendGrid  │ │ - R2        │ │ - Apple IAP │ │ - Cron jobs │
│ - Gemini    │ │ - Templates │ │ - Cloudinary│ │ - Google IAP│ │ - Email jobs│
│ - Router    │ │             │ │ - Local     │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## Component Map

### Core Components (Required)

These are the foundation - always keep them:

| Component | Files | Purpose |
|-----------|-------|---------|
| Config | `app/core/config.py` | Environment configuration |
| Database | `app/core/db.py` | Async database connection |
| Security | `app/core/security.py` | JWT verification |
| Exceptions | `app/core/exceptions.py` | Error handling |
| Base Model | `app/models/base.py` | BaseModel, SoftDeleteMixin |
| Dependencies | `app/api/deps.py` | DBSession, CurrentUser |
| CRUD Base | `app/business/crud_base.py` | Generic CRUD operations |

### Optional Components

| Component | Files | Dependencies | When to Remove |
|-----------|-------|--------------|----------------|
| **AI Gateway** | `app/services/ai/`, `app/api/v1/app/ai.py`, `app/schemas/ai.py` | openai, anthropic | No AI features needed |
| **Email Service** | `app/services/email/`, `app/jobs/email_jobs.py` | resend, sendgrid, jinja2 | Using Supabase/Clerk email or none |
| **Storage Service** | `app/services/storage/`, `app/api/v1/app/files.py`, `app/models/file.py` | aioboto3, cloudinary | Using Supabase Storage or none |
| **Stripe Payments** | `app/services/payments/stripe_service.py`, `app/business/billing_service.py`, `app/api/v1/app/billing.py` | stripe | No web payments |
| **Apple IAP** | `app/services/payments/apple_iap_service.py`, part of `app/business/iap_service.py` | None | No iOS app |
| **Google IAP** | `app/services/payments/google_iap_service.py`, part of `app/business/iap_service.py` | None | No Android app |
| **Background Jobs** | `app/jobs/` | arq | No async processing needed |
| **Prometheus Metrics** | `app/core/metrics.py`, `app/api/v1/public/metrics.py` | prometheus-client | No metrics needed |
| **Grafana Dashboards** | `grafana/dashboards/*.json`, `grafana/README.md` | None (Grafana external) | Not using Grafana |
| **Sentry** | `app/core/sentry.py` | sentry-sdk | No error tracking needed |
| **OpenTelemetry** | `app/core/tracing.py` | opentelemetry-* | No distributed tracing needed |
| **Load Tests** | `tests/load/` | locust | No load testing |

---

## Common Configurations

### Config 1: API Only (Minimal)

For a simple REST API without external services.

**Keep:**
- Core (config, db, security, exceptions)
- User model and endpoints
- CRUD patterns
- Health endpoints

**Remove:**
- AI Gateway
- Email Service
- Storage Service
- Payments (all)
- Background Jobs
- Observability

**Resulting structure:**
```
app/
├── api/v1/
│   ├── public/health.py
│   └── app/users.py
├── core/
│   ├── config.py, db.py, security.py, exceptions.py
├── models/
│   ├── base.py, user.py
├── business/
│   ├── crud_base.py, user_service.py
└── main.py
```

---

### Config 2: SaaS Backend (Postgres + Stripe + Auth)

For a typical SaaS application with subscriptions.

**Keep:**
- Core (all)
- User, Project models
- Stripe payments
- Billing endpoints
- Webhooks (Stripe, Supabase/Clerk)
- Background jobs (optional)

**Remove:**
- AI Gateway
- Email Service (or keep for transactional emails)
- Storage Service
- Apple/Google IAP
- Load tests

**Resulting structure:**
```
app/
├── api/v1/
│   ├── public/
│   │   ├── health.py
│   │   └── webhooks.py      # Stripe + Auth webhooks
│   ├── app/
│   │   ├── users.py
│   │   ├── projects.py
│   │   └── billing.py
│   └── admin/users.py
├── core/                     # Keep all
├── models/
│   ├── base.py, user.py, project.py
│   └── webhook_event.py
├── business/
│   ├── crud_base.py
│   ├── user_service.py
│   ├── project_service.py
│   └── billing_service.py
├── services/payments/
│   └── stripe_service.py
└── jobs/                     # Optional
```

---

### Config 3: AI Application

For an AI-powered application.

**Keep:**
- Core (all)
- AI Gateway
- User model
- Rate limiting (important for AI)

**Remove:**
- Storage Service (unless storing generated content)
- Payments (unless monetizing AI)
- Email Service
- Apple/Google IAP

**Resulting structure:**
```
app/
├── api/v1/
│   ├── public/health.py
│   └── app/
│       ├── users.py
│       └── ai.py
├── core/                     # Keep all, especially rate limiting
├── models/
│   ├── base.py, user.py
├── business/
│   ├── crud_base.py, user_service.py
├── services/ai/             # Keep all providers you need
│   ├── base.py
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   ├── router.py
│   └── factory.py
└── schemas/ai.py
```

---

### Config 4: Mobile App Backend

For iOS/Android app with in-app purchases.

**Keep:**
- Core (all)
- User model (with IAP fields)
- Apple IAP service
- Google IAP service
- IAP business logic
- Apple/Google webhooks
- Background jobs (for sync)

**Remove:**
- AI Gateway
- Stripe (unless also have web)
- Email Service (push notifications instead)
- Storage Service (unless user uploads)

**Resulting structure:**
```
app/
├── api/v1/
│   ├── public/
│   │   ├── health.py
│   │   └── webhooks.py      # Apple + Google webhooks
│   └── app/users.py
├── core/                     # Keep all
├── models/
│   ├── base.py
│   ├── user.py              # With apple_original_transaction_id, google_purchase_token
│   └── webhook_event.py
├── business/
│   ├── crud_base.py
│   ├── user_service.py
│   └── iap_service.py
├── services/payments/
│   ├── apple_iap_service.py
│   └── google_iap_service.py
└── jobs/                     # For subscription sync
```

---

## Removal Instructions

### Remove AI Gateway

```bash
# Remove files
rm -rf app/services/ai
rm app/api/v1/app/ai.py
rm app/schemas/ai.py

# Update router.py - remove these lines:
# from app.api.v1.app import ai
# app_router.include_router(ai.router, prefix="/ai")

# Update pyproject.toml - remove ai optional deps or don't install them:
# pip install -e "."  # Instead of pip install -e ".[ai]"
```

### Remove Email Service

```bash
# Remove files
rm -rf app/services/email
rm app/jobs/email_jobs.py  # If exists

# Update jobs/__init__.py if needed
# Update pyproject.toml - remove email deps
```

### Remove Storage Service

```bash
# Remove files
rm -rf app/services/storage
rm app/api/v1/app/files.py
rm app/models/file.py
rm app/schemas/file.py

# Remove migration for file table (if already run, create a new migration to drop it)

# Update router.py - remove:
# from app.api.v1.app import files
# app_router.include_router(files.router, prefix="/files")

# Update User model - remove relationship:
# files: list["File"] = Relationship(back_populates="owner")
```

### Remove Stripe Payments

```bash
# Remove files
rm app/services/payments/stripe_service.py
rm app/business/billing_service.py
rm app/api/v1/app/billing.py

# Update webhooks.py - remove Stripe webhook handler
# Update router.py - remove billing router
# Update User model - remove stripe fields (create migration)
```

### Remove Apple/Google IAP

```bash
# Remove files
rm app/services/payments/apple_iap_service.py
rm app/services/payments/google_iap_service.py
rm app/business/iap_service.py

# Update webhooks.py - remove Apple/Google handlers
# Update User model - remove IAP fields (create migration)
# Update tests - remove IAP tests
```

### Remove Background Jobs

```bash
# Remove directory
rm -rf app/jobs

# Remove worker commands from Makefile
# Remove worker service from docker-compose.yml
# Remove arq from dependencies
```

### Remove Observability

```bash
# Remove Sentry
rm app/core/sentry.py
# Update main.py - remove init_sentry() call

# Remove Metrics
rm app/core/metrics.py
rm app/api/v1/public/metrics.py
# Update router.py - remove metrics router

# Remove OpenTelemetry Tracing
rm app/core/tracing.py
# Update main.py - remove tracing imports and calls:
#   - init_tracing()
#   - instrument_app()
#   - instrument_httpx()
#   - instrument_redis()
#   - shutdown_tracing()
# Update app/core/logging.py - remove _get_trace_context() method
```

---

## Minimal Setups

### Absolute Minimum (API Skeleton)

Files to keep:

```
app/
├── __init__.py
├── main.py                   # Simplified version
├── api/
│   ├── __init__.py
│   ├── deps.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       └── public/
│           ├── __init__.py
│           └── health.py
├── core/
│   ├── __init__.py
│   ├── config.py             # Minimal config
│   ├── db.py
│   └── exceptions.py
├── models/
│   ├── __init__.py
│   └── base.py
└── schemas/
    ├── __init__.py
    └── common.py
```

Minimal `.env`:
```bash
SECRET_KEY="your-secret-key-at-least-32-characters"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/myapp"
```

Minimal `pyproject.toml` dependencies:
```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.22",
    "asyncpg>=0.30.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
]
```

---

### Your Stack: Postgres + Stripe + Supabase

Here's exactly what to keep and remove:

**Keep these directories/files:**

```
app/
├── api/
│   ├── deps.py
│   └── v1/
│       ├── router.py
│       ├── public/
│       │   ├── health.py
│       │   └── webhooks.py    # Keep Stripe + Supabase handlers only
│       ├── app/
│       │   ├── users.py
│       │   ├── projects.py    # Your resources
│       │   └── billing.py
│       └── admin/
│           └── users.py
├── core/                       # Keep ALL
├── models/
│   ├── base.py
│   ├── user.py
│   ├── project.py
│   └── webhook_event.py
├── schemas/
│   ├── common.py
│   ├── user.py
│   └── project.py
├── business/
│   ├── crud_base.py
│   ├── user_service.py
│   ├── project_service.py
│   └── billing_service.py
└── services/
    └── payments/
        └── stripe_service.py
```

**Remove these:**

```bash
# AI (not needed)
rm -rf app/services/ai
rm -f app/api/v1/app/ai.py
rm -f app/schemas/ai.py

# Storage (using Supabase Storage instead)
rm -rf app/services/storage
rm -f app/api/v1/app/files.py
rm -f app/models/file.py
rm -f app/schemas/file.py

# Email (optional - using Supabase email)
rm -rf app/services/email

# Mobile IAP (web only)
rm -f app/services/payments/apple_iap_service.py
rm -f app/services/payments/google_iap_service.py
rm -f app/business/iap_service.py

# Background jobs (optional)
rm -rf app/jobs

# Load tests (optional)
rm -rf tests/load
```

**Update webhooks.py:**

Keep only:
- `@router.post("/stripe")` - Stripe webhooks
- `@router.post("/supabase")` - Supabase auth webhooks

Remove:
- `@router.post("/clerk")` - Not using Clerk
- `@router.post("/apple")` - Not using iOS
- `@router.post("/google")` - Not using Android

**Update User model:**

Remove IAP fields if not needed:
```python
# Remove these lines from app/models/user.py:
# apple_original_transaction_id: str | None = ...
# google_purchase_token: str | None = ...
```

**Update router.py:**

```python
# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.admin import users as admin_users
from app.api.v1.app import billing, projects, users
from app.api.v1.public import health, webhooks

# Public routes (no auth required)
public_router = APIRouter(prefix="/public", tags=["Public"])
public_router.include_router(health.router)
public_router.include_router(webhooks.router, prefix="/webhooks")

# App routes (auth required)
app_router = APIRouter(prefix="/app", tags=["App"])
app_router.include_router(users.router, prefix="/users")
app_router.include_router(projects.router, prefix="/projects")
app_router.include_router(billing.router, prefix="/billing")

# Admin routes (auth + admin role required)
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
admin_router.include_router(admin_users.router, prefix="/users")

# Aggregate all v1 routes
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(public_router)
api_router.include_router(app_router)
api_router.include_router(admin_router)
```

**Install only needed dependencies:**

```bash
pip install -e ".[payments]"  # Just Stripe
# Or manually:
pip install stripe
```

---

## Adding Components Back

### Re-add AI Gateway

1. Copy from original boilerplate:
   - `app/services/ai/`
   - `app/api/v1/app/ai.py`
   - `app/schemas/ai.py`

2. Update `router.py`:
   ```python
   from app.api.v1.app import ai
   app_router.include_router(ai.router, prefix="/ai")
   ```

3. Install dependencies:
   ```bash
   pip install openai anthropic
   ```

4. Add config:
   ```bash
   OPENAI_API_KEY="sk-..."
   AI_DEFAULT_PROVIDER="openai"
   ```

### Re-add Storage Service

1. Copy from original:
   - `app/services/storage/`
   - `app/api/v1/app/files.py`
   - `app/models/file.py`
   - `app/schemas/file.py`

2. Update `router.py`

3. Run migration:
   ```bash
   make migrate msg="add file model"
   ```

4. Install dependencies:
   ```bash
   pip install aioboto3  # For S3/R2
   # or
   pip install cloudinary
   ```

### Re-add Background Jobs

1. Copy from original:
   - `app/jobs/`

2. Install ARQ:
   ```bash
   pip install arq
   ```

3. Add Redis URL to config

4. Add to Makefile:
   ```makefile
   worker:
       arq app.jobs.worker.WorkerSettings
   ```

---

## Dependency Groups

The `pyproject.toml` has optional dependency groups:

```toml
[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy", ...]
ai = ["openai", "anthropic"]
email = ["resend", "sendgrid", "jinja2"]
storage = ["aioboto3", "cloudinary"]
payments = ["stripe"]
observability = ["sentry-sdk[fastapi]", "prometheus-client"]
loadtest = ["locust"]
all = ["omnistack-backend[dev,ai,email,storage,payments,observability]"]
```

Install what you need:

```bash
# Development only
pip install -e ".[dev]"

# Production with Stripe only
pip install -e ".[payments]"

# Full stack
pip install -e ".[all]"

# Custom combination
pip install -e ".[dev,payments,observability]"
```
