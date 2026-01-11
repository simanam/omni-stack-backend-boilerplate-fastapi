# OmniStack Backend Boilerplate - AI Context

> **Read this file first** to understand the project and continue development.

---

## Project Overview

**What:** Production-ready FastAPI backend boilerplate for SaaS applications
**Goal:** "Zero to API in 60 seconds, Zero to Production in 60 minutes"
**Stack:** Python 3.12+, FastAPI, SQLModel, PostgreSQL, Redis, ARQ

---

## Current Status

| Metric | Value |
|--------|-------|
| **Current Phase** | Phase 10: Deployment |
| **Phase 9 Status** | ✅ Complete & Verified |
| **Overall Progress** | 92/126 tasks (73%) |
| **v1.0 Progress** | 92/118 tasks (78%) |

---

## Resume Instructions

**To continue development in a new conversation:**

1. **Start Docker services:**
   ```bash
   # IMPORTANT: Stop local Postgres if running (conflicts with Docker)
   brew services stop postgresql@17  # or your version

   # Start Docker services
   make up
   ```

2. **Activate environment:**
   ```bash
   source .venv/bin/activate
   ```

3. **Verify everything works:**
   ```bash
   make dev  # Start server (Ctrl+C to stop)
   # In another terminal:
   curl http://localhost:8000/api/v1/public/health/ready
   # Should return: {"status":"healthy",...}
   ```

4. **Run tests:**
   ```bash
   make test  # Should pass 189/190 tests (1 pre-existing async issue)
   make lint  # Should pass all checks
   ```

5. **Start Phase 10 implementation** (see below)

---

## Phase Summary

| Phase | Name | Tasks | Status |
|-------|------|-------|--------|
| 1 | Foundation | 10 | ✅ Complete & Verified |
| 2 | Authentication | 8 | ✅ Complete & Verified |
| 3 | CRUD Patterns | 8 | ✅ Complete & Verified |
| 4 | Middleware & Security | 10 | ✅ Complete & Verified |
| 5 | Background Jobs | 10 | ✅ Complete & Verified |
| 6 | External Services | 12 | ✅ Complete & Verified |
| 7 | AI Gateway | 10 | ✅ Complete & Verified |
| 8 | Payments & Webhooks | 12 | ✅ Complete & Verified |
| 9 | Testing | 12 | ✅ Complete & Verified |
| 10 | Deployment | 13 | 🟡 Ready to Start |
| 11 | Documentation | 13 | 🔴 Not Started |
| 12 | Advanced (v1.1) | 8 | 🔴 Not Started |

---

## Phase 1 Complete - Files Created

### Core Application
- `app/main.py` - FastAPI app with lifespan handler
- `app/core/config.py` - Pydantic Settings (all env vars)
- `app/core/db.py` - Async SQLModel database layer
- `app/core/cache.py` - Redis cache utilities
- `app/core/exceptions.py` - Custom exception classes
- `app/models/base.py` - BaseModel with UUID, timestamps, SoftDeleteMixin
- `app/schemas/common.py` - HealthResponse, PaginatedResponse, ErrorResponse

### API Layer
- `app/api/deps.py` - DBSession dependency
- `app/api/v1/router.py` - Router aggregation (public, app, admin)
- `app/api/v1/public/health.py` - `/health` and `/health/ready` endpoints

### Infrastructure
- `pyproject.toml` - All dependencies + ruff/pytest config
- `Makefile` - Dev commands (venv, install, dev, up, down, test, lint)
- `alembic.ini` + `migrations/env.py` - Async Alembic setup
- `docker/Dockerfile` - Multi-stage production build
- `docker/Dockerfile.dev` - Development with hot reload
- `docker/docker-compose.yml` - Postgres, Redis, API services
- `.env.example` - All environment variables documented
- `.gitignore` - Python/IDE/env exclusions
- `README.md` - Quick start guide

### Testing
- `tests/conftest.py` - Pytest fixtures with async support
- `tests/unit/test_health.py` - Health endpoint tests

---

## Phase 2 Complete - Files Created

### Authentication
- `app/core/security.py` - JWT verification (RS256/HS256), `verify_token()`, `require_role()`
- `app/models/user.py` - User model with Stripe subscription fields
- `app/schemas/user.py` - UserCreate, UserUpdate, UserRead, UserReadAdmin
- `app/business/user_service.py` - User sync service, CRUD operations
- `app/api/deps.py` - Updated with `CurrentUser`, `CurrentUserId`, `TokenPayload`
- `app/api/v1/app/users.py` - `GET /me`, `PATCH /me` endpoints
- `app/api/v1/admin/users.py` - Admin user management endpoints
- `migrations/versions/20260110_*_add_user_model.py` - User table migration

### New API Endpoints
- `GET /api/v1/app/users/me` - Get current user profile
- `PATCH /api/v1/app/users/me` - Update current user profile
- `GET /api/v1/admin/users` - List all users (admin)
- `GET /api/v1/admin/users/{id}` - Get user by ID (admin)
- `PATCH /api/v1/admin/users/{id}` - Update user (admin)
- `POST /api/v1/admin/users/{id}/deactivate` - Deactivate user (admin)
- `POST /api/v1/admin/users/{id}/activate` - Activate user (admin)

---

## Phase 3 Complete - Files Created

### CRUD Patterns
- `app/business/crud_base.py` - Generic CRUD base class with:
  - `get()`, `get_multi()`, `get_by_field()`, `count()`
  - `get_multi_by_owner()`, `count_by_owner()`
  - `create()`, `create_with_owner()`, `update()`
  - `delete()`, `soft_delete()`, `restore()`
- `app/models/project.py` - Project model (BaseModel + SoftDeleteMixin)
- `app/schemas/project.py` - ProjectCreate, ProjectUpdate, ProjectRead
- `app/business/project_service.py` - Project service extending CRUDBase
- `app/api/v1/app/projects.py` - Full CRUD endpoints with ownership checks
- `app/utils/pagination.py` - Pagination utilities (PaginationParams, PageParams, paginate)
- `migrations/versions/20260110_*_add_project_model.py` - Project table migration

### New API Endpoints
- `GET /api/v1/app/projects` - List user's projects (paginated, searchable)
- `POST /api/v1/app/projects` - Create new project
- `GET /api/v1/app/projects/{id}` - Get project by ID
- `PATCH /api/v1/app/projects/{id}` - Update project
- `DELETE /api/v1/app/projects/{id}` - Delete project (soft delete)

---

## Phase 4 Complete - Files Created

### Middleware (`app/core/middleware.py`)
- `RateLimitConfig` - Parse "60/minute" format
- `RateLimiter` - Sliding window with Redis/memory fallback
- `RateLimitMiddleware` - Apply limits per route, skip health endpoints
- `SecurityHeadersMiddleware` - X-Content-Type-Options, X-Frame-Options, CSP, HSTS (prod only)
- `RequestIDMiddleware` - UUID per request, preserves client-provided ID
- `RequestLoggingMiddleware` - Structured request/response logging
- `register_middleware()` - Helper to register all middleware in correct order

### Utilities
- `app/utils/validators.py` - Input validation:
  - Email, URL, UUID validation
  - HTML sanitization (XSS prevention)
  - Path traversal prevention
  - File type validation
  - Pydantic annotated types: `ValidatedEmail`, `ValidatedURL`, `SanitizedString`
- `app/utils/crypto.py` - Cryptographic utilities:
  - Token generation (`generate_token()`, `generate_api_key()`)
  - HMAC signing/verification (for webhooks)
  - Password hashing (PBKDF2-SHA256)
  - SHA-256/512 hashing
- `app/utils/resilience.py` - Resilience patterns:
  - `CircuitBreaker` - Prevent cascading failures
  - `retry_async()` / `@with_retry` - Exponential backoff
  - `with_timeout()` / `@timeout` - Async timeouts
  - `with_fallback()` - Fallback on failure
  - `resilient_call()` - Combined patterns

### Tests
- `tests/unit/test_middleware.py` - 16 tests for middleware

### Response Headers (on all endpoints)
- `X-Request-ID` - Unique request identifier
- `X-RateLimit-Limit` - Requests allowed per window
- `X-RateLimit-Remaining` - Requests remaining
- `X-RateLimit-Reset` - Window reset timestamp
- Security headers (CSP, X-Frame-Options, etc.)

---

## Phase 5 Complete - Files Created

### Background Jobs
- `app/jobs/worker.py` - ARQ worker configuration with:
  - `get_redis_settings()` - Parse REDIS_URL for ARQ
  - `WorkerSettings` class with functions, cron_jobs, timeouts
  - Startup/shutdown lifecycle hooks
- `app/jobs/__init__.py` - Job enqueue utilities:
  - `get_job_pool()` - Get/create ARQ connection pool
  - `enqueue()` - Queue jobs with optional delay and deduplication
  - `enqueue_in()` - Queue jobs with delay
  - Sync fallback when Redis unavailable
- `app/jobs/email_jobs.py` - Email background tasks:
  - `send_welcome_email()` - Welcome new users
  - `send_password_reset_email()` - Password reset flow
  - `send_notification_email()` - Generic notifications
- `app/jobs/report_jobs.py` - Report generation tasks:
  - `generate_daily_report()` - Daily usage report (cron)
  - `export_user_data()` - GDPR data export
  - `cleanup_old_data()` - Weekly maintenance (cron)
- `app/jobs/decorators.py` - Job helper decorators:
  - `@retry()` - Retry with exponential backoff
  - `@timeout()` - Job execution timeout
  - `@background_task()` - Combined retry + timeout
- `app/api/v1/admin/jobs.py` - Job monitoring endpoints:
  - `GET /api/v1/admin/jobs` - List recent jobs
  - `GET /api/v1/admin/jobs/{id}` - Get job status
  - `POST /api/v1/admin/jobs/{id}/retry` - Retry failed job
  - `DELETE /api/v1/admin/jobs/{id}` - Cancel pending job

### Infrastructure Updates
- `Makefile` - Added `make worker` and `make worker-dev` commands
- `docker/docker-compose.yml` - Added worker service with `--profile worker`

### Tests
- `tests/unit/test_jobs.py` - 20 tests for background job system

---

## Phase 6 Complete - Files Created

### Email Service (`app/services/email/`)
- `app/services/email/base.py` - Abstract email interface:
  - `BaseEmailService` abstract class
  - `EmailResult` dataclass
  - `send()`, `send_raw()`, `send_bulk()` methods
- `app/services/email/resend_provider.py` - Resend implementation
- `app/services/email/sendgrid_provider.py` - SendGrid implementation
- `app/services/email/console_provider.py` - Console fallback (dev)
- `app/services/email/factory.py` - Provider factory (`get_email_service()`)
- `app/services/email/renderer.py` - Jinja2 template renderer
- `app/services/email/templates/` - Email templates:
  - `base.html` - Base template with styling
  - `welcome.html` - Welcome email
  - `password_reset.html` - Password reset email
  - `notification.html` - Generic notification

### Storage Service (`app/services/storage/`)
- `app/services/storage/base.py` - Abstract storage interface:
  - `BaseStorageService` abstract class
  - `StorageFile`, `PresignedUrl` dataclasses
  - `upload()`, `download()`, `delete()`, `exists()`
  - `get_presigned_upload_url()`, `get_presigned_download_url()`
  - `list_files()`
- `app/services/storage/s3_provider.py` - AWS S3 implementation
- `app/services/storage/r2_provider.py` - Cloudflare R2 implementation
- `app/services/storage/cloudinary_provider.py` - Cloudinary implementation
- `app/services/storage/local_provider.py` - Local filesystem (dev)
- `app/services/storage/factory.py` - Provider factory (`get_storage_service()`)

### File Upload API
- `app/models/file.py` - File model (tracks uploaded files)
- `app/schemas/file.py` - File schemas (FileUploadRequest, FileRead, etc.)
- `app/api/v1/app/files.py` - File endpoints
- `migrations/versions/20260110_*_add_file_model.py` - File table migration

### New API Endpoints
- `POST /api/v1/app/files/upload-url` - Get presigned upload URL
- `POST /api/v1/app/files/confirm` - Confirm upload completed
- `GET /api/v1/app/files` - List user's files
- `GET /api/v1/app/files/{id}` - Get file metadata
- `GET /api/v1/app/files/{id}/download-url` - Get download URL
- `DELETE /api/v1/app/files/{id}` - Delete file

### Configuration
- `EMAIL_PROVIDER`: `resend` | `sendgrid` | `console` (default)
- `STORAGE_PROVIDER`: `s3` | `r2` | `cloudinary` | `local` (default)

---

## Phase 7 Complete - Files Created

### AI Service (`app/services/ai/`)
- `app/services/ai/base.py` - Abstract LLM interface:
  - `BaseLLMProvider` abstract class
  - `LLMResponse`, `Message`, `Role` dataclasses
  - `ModelComplexity` enum (simple, moderate, complex, search)
  - `complete()`, `stream()`, `complete_simple()`, `stream_simple()` methods
- `app/services/ai/openai_provider.py` - OpenAI implementation (gpt-4o default)
- `app/services/ai/anthropic_provider.py` - Anthropic implementation (claude-sonnet-4-5 default)
- `app/services/ai/gemini_provider.py` - Google Gemini implementation (gemini-2.5-flash default)
- `app/services/ai/router.py` - Smart LLM router:
  - `LLMRouter` class for cost-optimized routing
  - `ModelRoute` dataclass
  - Routes by complexity: simple→gpt-4o-mini, moderate→gpt-4o, complex→claude-sonnet-4-5
- `app/services/ai/factory.py` - Provider factory (`get_llm_provider()`)

### AI API
- `app/schemas/ai.py` - AI schemas:
  - `ChatMessage`, `CompletionRequest`, `SimpleCompletionRequest`
  - `RoutedCompletionRequest`, `CompletionResponse`, `AIStatusResponse`
- `app/api/v1/app/ai.py` - AI endpoints with streaming support

### New API Endpoints
- `GET /api/v1/app/ai/status` - Get AI service status and providers
- `POST /api/v1/app/ai/completions` - Chat completion (supports streaming)
- `POST /api/v1/app/ai/chat` - Simple prompt-based chat (supports streaming)
- `POST /api/v1/app/ai/chat/routed` - Smart routed chat (auto-selects model by complexity)

### Configuration
- `AI_DEFAULT_PROVIDER`: `openai` | `anthropic` | `gemini` (default: openai)
- `AI_DEFAULT_MODEL`: Model name (default: gpt-4o)
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `GOOGLE_API_KEY`: Google API key (for Gemini)

---

## Phase 8 Complete - Files Created

### Stripe Service (`app/services/payments/`)
- `app/services/payments/__init__.py` - Package exports
- `app/services/payments/stripe_service.py` - Stripe API wrapper:
  - `StripeService` class with customer, checkout, portal, subscription methods
  - `create_customer()`, `get_customer()`, `update_customer()`
  - `create_checkout_session()`, `create_portal_session()`
  - `get_subscription()`, `cancel_subscription()`, `update_subscription()`
  - `get_invoices()`, `construct_webhook_event()`
  - `get_stripe_service()` factory function

### Billing Service (`app/business/`)
- `app/business/billing_service.py` - Billing business logic:
  - `BillingService` class for subscription management
  - `get_or_create_customer()`, `get_billing_status()`
  - `start_checkout()`, `get_billing_portal_url()`
  - `sync_subscription_status()`, `cancel_subscription()`
  - Webhook handlers: `handle_checkout_completed()`, `handle_subscription_updated()`

### Billing API (`app/api/v1/app/`)
- `app/api/v1/app/billing.py` - Billing endpoints:
  - `GET /api/v1/app/billing/status` - Current subscription status
  - `POST /api/v1/app/billing/checkout` - Start checkout session
  - `GET /api/v1/app/billing/portal` - Get billing portal URL
  - `GET /api/v1/app/billing/invoices` - List invoices
  - `POST /api/v1/app/billing/cancel` - Cancel subscription
  - `POST /api/v1/app/billing/resume` - Resume cancelled subscription

### Webhook Handlers (`app/api/v1/public/`)
- `app/api/v1/public/webhooks.py` - Webhook endpoints:
  - `POST /api/v1/public/webhooks/stripe` - Stripe webhooks
  - `POST /api/v1/public/webhooks/clerk` - Clerk user sync
  - `POST /api/v1/public/webhooks/supabase` - Supabase auth events
  - `POST /api/v1/public/webhooks/apple` - Apple App Store notifications
  - `POST /api/v1/public/webhooks/google` - Google Play notifications
  - Idempotency tracking with `WebhookEvent` model

### Mobile In-App Purchase Services (`app/services/payments/`)
- `app/services/payments/apple_iap_service.py` - Apple App Store Server Notifications V2:
  - JWS decoding and verification
  - Notification type handling (SUBSCRIBED, DID_RENEW, EXPIRED, REFUND, REVOKE)
  - Bundle ID verification
- `app/services/payments/google_iap_service.py` - Google Play Real-time Developer Notifications:
  - Pub/Sub message decoding
  - Notification type handling (PURCHASED, RENEWED, CANCELED, EXPIRED, REVOKED)
  - Package name verification
- `app/business/iap_service.py` - Mobile IAP business logic:
  - `handle_apple_notification()`, `handle_google_notification()`
  - `link_apple_subscription()`, `link_google_subscription()`
  - Subscription sync and plan mapping

### Webhook Event Model
- `app/models/webhook_event.py` - Event tracking:
  - `WebhookEvent` model with provider, event_type, idempotency_key
  - JSONB payload storage, status tracking, error handling
- `migrations/versions/20260110_210000_add_webhook_event_model.py`

### Feature Flags (`app/core/`)
- `app/core/feature_flags.py` - Plan-based feature gating:
  - `PLAN_LIMITS` configuration (free, pro, enterprise)
  - `FeatureFlags` class with Redis-backed usage tracking
  - `check_feature()`, `increment_usage()`, `get_remaining()`
  - Monthly reset with automatic TTL

### Configuration
- `STRIPE_SECRET_KEY`: Stripe API key
- `STRIPE_WEBHOOK_SECRET`: Webhook signature verification
- `STRIPE_PRICE_ID_MONTHLY`: Monthly subscription price ID
- `STRIPE_PRICE_ID_YEARLY`: Yearly subscription price ID
- `APPLE_BUNDLE_ID`: Apple app bundle ID (e.g., "com.example.myapp")
- `APPLE_SHARED_SECRET`: Apple app-specific shared secret
- `GOOGLE_PLAY_PACKAGE_NAME`: Google Play package name
- `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`: Base64-encoded service account JSON

### Tests
- `tests/unit/test_apple_iap.py` - 28 tests for Apple IAP service
- `tests/unit/test_google_iap.py` - 28 tests for Google IAP service

---

## Phase 9 Complete - Files Created

### Unit Tests
- `tests/unit/test_billing.py` - 22 tests for billing service:
  - Customer creation, billing status, checkout, portal
  - Subscription sync, cancellation, resumption
  - Invoice retrieval, webhook handlers
- `tests/unit/test_webhooks.py` - 30 tests for webhook handlers:
  - Event idempotency (create, duplicate, mark processed/failed)
  - Stripe webhooks (checkout, subscription, invoices)
  - Clerk webhooks (user CRUD)
  - Supabase webhooks (user CRUD)

### Integration Tests
- `tests/integration/test_api_health.py` - 2 tests for health endpoints
- `tests/integration/test_api_users.py` - 11 tests for user endpoints
- `tests/integration/test_api_projects.py` - 14 tests for project CRUD
- `tests/integration/test_api_billing.py` - 13 tests for billing API

### Test Summary
- **Total tests**: 190 (up from 38)
- **New tests added**: 152 (including 56 IAP tests from Phase 8)
- **All linter checks pass**

---

## What To Do Next: Phase 10 (Deployment)

### Files to Create

1. **Production Dockerfile** - Optimize multi-stage build
2. **CI/CD Pipeline** - GitHub Actions workflows
3. **Kubernetes manifests** - Deployment configs
4. **Environment configs** - Production settings

### Reference Code

See `docs/omnistack-technical-prd.md`:
- **Section 13**: Deployment

---

## Quick Start Commands

```bash
# Setup (first time)
make venv                    # Create Python 3.12 venv
source .venv/bin/activate    # Activate venv
make install                 # Install dependencies

# Development
make up                      # Start Postgres + Redis (Docker)
make dev                     # Start API at localhost:8000
make worker                  # Start ARQ background worker
make worker-dev              # Start worker with auto-reload

# Testing
make test                    # Run pytest
make lint                    # Run ruff

# Database
make migrate msg="message"   # Generate + apply migrations
make down                    # Stop Docker services
```

---

## Key Architecture Patterns

### Configuration (`app/core/config.py`)
```python
from app.core.config import settings
# All config via environment variables
# Computed fields: async_database_url, jwks_url, jwt_algorithm
```

### Database Session (`app/api/deps.py`)
```python
from app.api.deps import DBSession, CurrentUser

@router.get("/items")
async def list_items(session: DBSession):
    # session is AsyncSession, auto-commits on success

@router.get("/me")
async def get_me(user: CurrentUser):
    # user is User model, auto-synced from JWT on first request
```

### Base Model (`app/models/base.py`)
```python
from app.models.base import BaseModel, SoftDeleteMixin

class MyModel(BaseModel, table=True):
    # Gets: id (UUID), created_at, updated_at
    name: str
```

### CRUD Base (`app/business/crud_base.py`)
```python
from app.business.crud_base import CRUDBase

class MyService(CRUDBase[MyModel, MyCreate, MyUpdate]):
    pass

my_service = MyService(MyModel)
item = await my_service.get(session, id="123")
items = await my_service.get_multi_by_owner(session, owner_id=user.id)
```

### Custom Exceptions (`app/core/exceptions.py`)
```python
from app.core.exceptions import NotFoundError, ValidationError
raise NotFoundError("Project", project_id)
# Returns: {"error": {"code": "NOT_FOUND", "message": "...", "details": {...}}}
```

### Email Service (`app/services/email/`)
```python
from app.services.email import get_email_service

email = get_email_service()

# Send templated email
result = await email.send(
    to="user@example.com",
    subject="Welcome!",
    template="welcome",
    data={"name": "John"}
)

# Send raw HTML
result = await email.send_raw(
    to="user@example.com",
    subject="Hello",
    html_content="<h1>Hello World</h1>"
)
```

### Storage Service (`app/services/storage/`)
```python
from app.services.storage import get_storage_service

storage = get_storage_service()

# Get presigned upload URL
presigned = await storage.get_presigned_upload_url(
    key="uploads/user123/file.pdf",
    content_type="application/pdf"
)
# Returns: PresignedUrl(url=..., fields=..., expires_in=3600)

# Download file
data = await storage.download("uploads/user123/file.pdf")

# Delete file
await storage.delete("uploads/user123/file.pdf")
```

### Background Jobs (`app/jobs/`)
```python
from app.jobs import enqueue, enqueue_in

# Enqueue a job to run immediately
await enqueue(
    "app.jobs.email_jobs.send_welcome_email",
    user.email,
    user.full_name
)

# Enqueue a job to run in 60 seconds
await enqueue_in(
    "app.jobs.email_jobs.send_notification_email",
    60,  # defer by 60 seconds
    user.email,
    "Subject",
    "Body text"
)

# Use decorators for retry/timeout
from app.jobs.decorators import background_task

@background_task(max_attempts=3, timeout_seconds=300)
async def my_job(ctx, arg1, arg2):
    ...
```

### AI Service (`app/services/ai/`)
```python
from app.services.ai import get_llm_provider, get_llm_router, Message, Role

# Get default provider
provider = get_llm_provider()  # Uses AI_DEFAULT_PROVIDER

# Simple completion
response = await provider.complete_simple(
    "Explain quantum computing in one sentence",
    system="You are a helpful assistant"
)
print(response.content)  # "Quantum computing uses..."
print(response.usage)    # {"prompt_tokens": 12, "completion_tokens": 25, ...}

# Streaming
async for chunk in provider.stream_simple("Write a poem about Python"):
    print(chunk, end="")

# Smart routing by complexity
router = get_llm_router()
response = await router.chat(
    "Solve this complex math problem: ...",
    complexity="complex"  # Uses claude-sonnet-4-5
)

# Chat with message history
messages = [
    Message(role=Role.SYSTEM, content="You are a coding assistant"),
    Message(role=Role.USER, content="How do I reverse a list in Python?"),
]
response = await provider.complete(messages)
```

---

## Project Structure

```
backend-boilerplate-fastapi/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── deps.py             # Dependencies (DBSession, auth)
│   │   └── v1/
│   │       ├── router.py       # Route aggregator
│   │       ├── public/         # No auth (health, webhooks)
│   │       ├── app/            # Auth required
│   │       └── admin/          # Admin role required
│   ├── core/
│   │   ├── config.py           # Pydantic Settings
│   │   ├── db.py               # Database engine/session
│   │   ├── cache.py            # Redis client
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── middleware.py       # Rate limiting, security headers, logging
│   ├── models/                 # SQLModel models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # External services (ai, email, storage)
│   │   ├── email/              # Email providers (Resend, SendGrid, Console)
│   │   ├── storage/            # Storage providers (S3, R2, Cloudinary, Local)
│   │   └── ai/                 # AI providers (OpenAI, Anthropic, Gemini)
│   ├── business/               # Business logic (CRUD, services)
│   ├── jobs/                   # ARQ background tasks
│   └── utils/
│       ├── pagination.py       # Pagination utilities
│       ├── validators.py       # Input validation, sanitization
│       ├── crypto.py           # Hashing, tokens, HMAC
│       └── resilience.py       # Circuit breaker, retry, timeout
├── migrations/                 # Alembic
├── tests/
├── docker/
│   ├── Dockerfile              # Production
│   ├── Dockerfile.dev          # Development
│   └── docker-compose.yml      # Local services
├── docs/
│   ├── implementation/         # Phase checklists
│   ├── audit/                  # Progress tracking
│   └── omnistack-technical-prd.md  # Code examples
├── .env.example
├── pyproject.toml
├── Makefile
└── README.md
```

---

## Documentation References

| Document | Purpose |
|----------|---------|
| `docs/omnistack-technical-prd.md` | **Code examples for all features** |
| `docs/implementation/phase-6-external-services.md` | Phase 6 task checklist |
| `docs/implementation/MASTER-TRACKER.md` | All 124 tasks overview |
| `docs/audit/AUDIT-SUMMARY.md` | Detailed progress tracking |

---

## Environment Variables (Key)

```bash
# Required
SECRET_KEY="min-32-chars"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/omnistack"

# Optional
REDIS_URL="redis://localhost:6379/0"
AUTH_PROVIDER="supabase"  # supabase | clerk | custom
SUPABASE_PROJECT_URL="https://xxx.supabase.co"

# Email (Phase 6)
EMAIL_PROVIDER="console"  # resend | sendgrid | console
RESEND_API_KEY=""
SENDGRID_API_KEY=""

# Storage (Phase 6)
STORAGE_PROVIDER="local"  # s3 | r2 | cloudinary | local
AWS_S3_BUCKET=""
CLOUDINARY_CLOUD_NAME=""

# AI (Phase 7)
AI_DEFAULT_PROVIDER="openai"  # openai | anthropic | gemini
AI_DEFAULT_MODEL="gpt-4o"
OPENAI_API_KEY=""
ANTHROPIC_API_KEY=""
GOOGLE_API_KEY=""
```

See `.env.example` for all variables.

---

## Known Issues / Notes

1. **Local Postgres conflict**: If you have Homebrew Postgres running, it will conflict with Docker. Run `brew services stop postgresql@17` (or your version) before `make up`.

2. **pytest-asyncio**: Uses `asyncio_default_fixture_loop_scope = "session"` in pyproject.toml for proper async fixture handling.

3. **Health endpoints**: Located at `/api/v1/public/health` and `/api/v1/public/health/ready` (not root `/health`).

4. **Optional dependencies**: Install email/storage providers with `pip install -e ".[email,storage]"` or `pip install -e ".[all]"` for everything.

---

## Important Rules

1. **Follow phases in order** - Dependencies exist between phases
2. **Reference Technical PRD** - Has working code examples for each feature
3. **Update CLAUDE.md** - When phase status changes
4. **Test as you go** - Run `make test` after implementing features
5. **Run migrations** - After creating new models: `make migrate msg="add file model"`

---

*Last Updated: 2026-01-10*
*Phase 9 Complete & Verified - Ready for Phase 10: Deployment*
