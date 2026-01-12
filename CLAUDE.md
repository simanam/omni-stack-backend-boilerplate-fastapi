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
| **Current Phase** | Phase 12: Advanced (v1.1) - Complete |
| **v1.0 Status** | ✅ Complete (Phases 1-11) |
| **v1.1 Progress** | 8/8 features complete (API Versioning, WebSocket, Admin Dashboard, OpenTelemetry, Enhanced Metrics, Contact Form, Usage-Based Billing, SQLite Fallback) |
| **Overall Progress** | 123/123 tasks (100%) |
| **v1.0 Progress** | 115/115 tasks (100%) |
| **Unit Tests** | 430+ passing |
| **Documentation** | [Live on GitHub Pages](https://simanam.github.io/omni-stack-backend-boilerplate-fastapi/) |
| **License** | MIT |

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
   make test  # Should pass ~230 tests (unit + integration)
   make lint  # Should pass all checks
   ```

5. **Start Phase 12 implementation** (optional, for v1.1 features)

---

## Phase Summary

| Phase | Name | Tasks | Status |
|-------|------|-------|--------|
| 1 | Foundation | 10 | ✅ Complete |
| 2 | Authentication | 8 | ✅ Complete |
| 3 | CRUD Patterns | 8 | ✅ Complete |
| 4 | Middleware & Security | 10 | ✅ Complete |
| 5 | Background Jobs | 10 | ✅ Complete |
| 6 | External Services | 12 | ✅ Complete |
| 7 | AI Gateway | 10 | ✅ Complete |
| 8 | Payments & Webhooks | 12 | ✅ Complete |
| 9 | Testing | 12 | ✅ Complete |
| 10 | Deployment | 13 | ✅ Complete |
| 11 | Documentation | 10 | ✅ Complete |
| 12 | Advanced (v1.1) | 8 | ✅ Complete |

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

## Phase 10 Complete - Files Created

### Deployment Configs
- `railway.toml` - Railway deployment configuration
- `render.yaml` - Render blueprint (API + Worker + DB + Redis)
- `fly.toml` - Fly.io deployment configuration

### Observability (`app/core/`)
- `app/core/sentry.py` - Sentry error tracking:
  - `init_sentry()` - Initialize with environment-based config
  - `set_user_context()` - Add user info to errors
  - `capture_exception()`, `capture_message()` - Manual capture
  - `add_breadcrumb()`, `set_tag()`, `set_context()` - Debug context
  - Health check filtering, PII scrubbing
- `app/core/metrics.py` - Prometheus metrics:
  - Request metrics (count, latency, in-progress)
  - Database metrics (queries, pool stats, errors)
  - Cache metrics (hits, misses)
  - Job metrics (count, duration, queue size)
  - AI/LLM metrics (requests, tokens, latency)
  - External service metrics
  - Helper functions: `track_request_metrics()`, `track_db_query()`, etc.
- `app/core/logging.py` - Structured logging:
  - `JSONFormatter` - Production JSON logs
  - `DevelopmentFormatter` - Colored terminal logs
  - Request context via contextvars
  - `LogContext` context manager
  - `setup_logging()` - Auto-configure based on environment

### Metrics API
- `app/api/v1/public/metrics.py` - Prometheus endpoint:
  - `GET /api/v1/public/metrics` - Prometheus scrape endpoint
  - `GET /api/v1/public/metrics/health` - Metrics system health
  - Optional token-based auth for production

### CI/CD Pipelines (`.github/workflows/`)
- `.github/workflows/ci.yml` - CI pipeline:
  - Lint (ruff), Type check (mypy)
  - Unit tests, Integration tests
  - Coverage report (Codecov)
  - Docker image build
  - Security scan (safety, bandit)
- `.github/workflows/deploy.yml` - Deploy pipeline:
  - Build and push to GitHub Container Registry
  - Deploy to staging (Railway/Render/Fly.io)
  - Run smoke tests
  - Deploy to production
  - Sentry release tracking
  - Slack notifications
- `.github/workflows/security.yml` - Security scan:
  - Dependency scan (safety, pip-audit)
  - Code scan (bandit, semgrep)
  - Container scan (Trivy)
  - Secrets detection (gitleaks, trufflehog)
  - SAST (CodeQL)

### Documentation
- `docs/DEPLOYMENT.md` - Deployment guide:
  - Railway, Render, Fly.io deployment
  - Docker deployment
  - Database migrations
  - Rollback procedures
  - Scaling guidelines
  - Monitoring setup
- `docs/BACKUP.md` - Backup & recovery:
  - Database backup strategies
  - File storage backups
  - Recovery procedures
  - Disaster recovery plan

### Scripts
- `scripts/migrate_production.py` - Production migration tool:
  - Pre-migration health checks
  - Dry-run mode
  - Rollback support
  - Connection verification
  - Migration logging

### Load Tests
- `tests/load/locustfile.py` - Locust load tests:
  - `PublicUser` - Health check scenarios
  - `AuthenticatedUser` - CRUD operations
  - `BillingUser` - Subscription checks
  - `AIUser` - AI completion requests
  - `FileUser` - File upload scenarios
  - `SpikeUser` - Spike testing
  - `SoakUser` - Soak testing

### Docker Updates
- `docker/Dockerfile` - Production optimizations:
  - Multi-stage build
  - tini for signal handling
  - Non-root user
  - Health check command
  - uvloop + httptools for performance

### Configuration
- `SENTRY_DSN`: Sentry project DSN
- `SENTRY_TRACES_SAMPLE_RATE`: Trace sampling (default: 0.1)
- `METRICS_TOKEN`: Optional token for metrics endpoint protection

---

## Phase 11 Complete - Files Created

### Documentation (`documentation/`)
- `documentation/API-REFERENCE.md` - Complete API documentation:
  - All endpoints with request/response formats
  - Error codes and handling
  - Pagination patterns
  - Rate limiting headers
  - Authentication flow
- `documentation/GETTING-STARTED.md` - Developer onboarding:
  - Quick start guide
  - Environment variables reference
  - Docker setup
  - Troubleshooting guide
- `documentation/ARCHITECTURE.md` - System design:
  - Project structure
  - Layer architecture (API → Business → Data)
  - Naming conventions
  - Request lifecycle
  - Database patterns
  - Adding new features guide
- `documentation/MODULAR-GUIDE.md` - Component selection:
  - Component dependency map
  - Removal instructions for each service
  - Minimal setup configurations
  - Example: Postgres + Stripe + Supabase only
- `documentation/FRONTEND-INTEGRATION.md` - Client integration:
  - TypeScript types for all API responses
  - API client setup (fetch, axios)
  - React examples with React Query
  - Next.js (App Router) examples
  - React Native examples
  - Native iOS (Swift) examples
  - Native Android (Kotlin) examples
  - Error handling patterns
  - Streaming AI responses
- `documentation/CONTRIBUTING.md` - Contribution guidelines:
  - Code style (Ruff)
  - Testing requirements
  - PR process
  - Commit message conventions

### Documentation Hosting
- **Live Site**: https://simanam.github.io/omni-stack-backend-boilerplate-fastapi/
- **MkDocs Material**: Configured with `mkdocs.yml`
- **Deploy command**: `mkdocs gh-deploy`

### Documentation Summary
- **Total lines**: 6,400+
- **Platforms covered**: Web (React, Next.js), Mobile (React Native, iOS, Android)
- **All API endpoints documented**
- **TypeScript types for frontend**

---

## Phase 12.1 Complete - API Versioning

### Files Created
- `app/core/versioning.py` - Version utilities:
  - `APIVersion` enum (V1, V2) with parsing
  - `get_version_from_path()` - Extract version from URL
  - `get_version_from_header()` - Support Accept-Version, X-API-Version headers
  - `VersionInfo` - Deprecation info container
  - `add_version_headers()` - RFC 8594 compliant headers
  - `VersionMiddleware` - Auto-add version headers to responses
- `app/api/v2/__init__.py` - Version 2 package
- `app/api/v2/router.py` - v2 router aggregation
- `app/api/v2/public/health.py` - Enhanced health endpoints with latency metrics
- `app/api/v2/app/users.py` - User endpoints with metadata wrapper
- `tests/unit/test_versioning.py` - 38 unit tests

### Features
- Path-based version detection (`/api/v1/...`, `/api/v2/...`)
- Header-based version detection (Accept-Version, X-API-Version)
- Response headers: `X-API-Version`, `X-API-Latest-Version`
- Deprecation support: `Deprecation`, `Sunset`, `X-Deprecation-Notice`, `Link`
- v2 response format with metadata wrapper

### v2 Enhanced Response Format
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-01-11T12:00:00Z",
    "version": "v2"
  }
}
```

### New v2 Endpoints
- `GET /api/v2/public/health` - Enhanced with uptime, service info
- `GET /api/v2/public/health/ready` - Enhanced with latency metrics
- `GET /api/v2/app/users/me` - User profile with metadata wrapper
- `PATCH /api/v2/app/users/me` - Update profile with metadata wrapper

---

## Phase 12.2 Complete - WebSocket Support

### Files Created
- `app/services/websocket/__init__.py` - Package exports
- `app/services/websocket/manager.py` - Connection manager with Redis pub/sub
- `app/services/websocket/events.py` - Event types and message schemas
- `app/api/v1/app/ws.py` - WebSocket endpoints
- `tests/unit/test_websocket.py` - 23 unit tests

### Features
- JWT authentication via query parameter
- Connection tracking by user ID
- Channel/room subscriptions
- Broadcast to users, channels, or all
- Redis pub/sub for multi-instance support
- Presence tracking
- Ping/pong heartbeat

### New Endpoints
- `ws://host/api/v1/app/ws?token=<jwt>` - WebSocket connection
- `GET /api/v1/app/ws/status` - Connection statistics

---

## Phase 12.3 Complete - Admin Dashboard

### Files Created
- `app/models/audit_log.py` - Audit log model for tracking actions
- `app/models/feature_flag.py` - Feature flag model (boolean, percentage, user_list, plan_based)
- `app/api/v1/admin/dashboard.py` - Dashboard statistics endpoint
- `app/api/v1/admin/feature_flags.py` - Feature flags CRUD
- `app/api/v1/admin/impersonate.py` - User impersonation
- `migrations/versions/20260111_100000_add_audit_log_and_feature_flag_models.py` - Migration
- `tests/unit/test_admin_dashboard.py` - 31 unit tests

### New API Endpoints

**Dashboard:**
- `GET /api/v1/admin/dashboard/stats` - System statistics (users, subscriptions, webhooks, jobs)
- `GET /api/v1/admin/dashboard/audit-logs` - Audit log listing with filters
- `GET /api/v1/admin/dashboard/audit-logs/{id}` - Get specific audit log

**Feature Flags:**
- `GET /api/v1/admin/feature-flags` - List all flags
- `POST /api/v1/admin/feature-flags` - Create flag
- `GET /api/v1/admin/feature-flags/{id}` - Get flag by ID
- `GET /api/v1/admin/feature-flags/key/{key}` - Get flag by key
- `PATCH /api/v1/admin/feature-flags/{id}` - Update flag
- `DELETE /api/v1/admin/feature-flags/{id}` - Delete flag
- `POST /api/v1/admin/feature-flags/{id}/enable` - Enable flag
- `POST /api/v1/admin/feature-flags/{id}/disable` - Disable flag
- `POST /api/v1/admin/feature-flags/{id}/add-user` - Add user to flag
- `POST /api/v1/admin/feature-flags/{id}/remove-user` - Remove user from flag
- `GET /api/v1/admin/feature-flags/check/{key}` - Check flag for user

**Impersonation:**
- `POST /api/v1/admin/impersonate/start` - Start impersonation (creates JWT)
- `POST /api/v1/admin/impersonate/stop` - Stop impersonation (audit log)
- `GET /api/v1/admin/impersonate/active` - List recent impersonations

### Feature Flag Types
- **boolean** - Simple on/off toggle
- **percentage** - Enable for X% of users (consistent hashing)
- **user_list** - Enable for specific user IDs
- **plan_based** - Enable for specific subscription plans (free, pro, enterprise)

---

## Phase 12.4 Complete - OpenTelemetry Tracing

### Files Created
- `app/core/tracing.py` - OpenTelemetry setup:
  - `init_tracing()` - Initialize OpenTelemetry SDK
  - `instrument_app()` - FastAPI instrumentation
  - `instrument_sqlalchemy()` - Database query tracing
  - `instrument_redis()` - Redis operations tracing
  - `instrument_httpx()` - HTTP client tracing
  - `create_span()` - Manual span creation context manager
  - `@trace_function` - Function decorator for tracing
  - `get_current_trace_id()`, `get_current_span_id()` - Trace context access
  - `set_span_attribute()`, `set_span_status()`, `record_exception()` - Span helpers
  - NoOp implementations for graceful fallback
- `tests/unit/test_tracing.py` - 38 unit tests

### Features
- Auto-instrumentation for FastAPI, SQLAlchemy, Redis, httpx
- Manual span creation via `create_span()` context manager
- Function decorator `@trace_function` for tracing functions
- Multiple exporter support: OTLP, Zipkin, Console
- W3C Trace Context propagation
- Trace ID and span ID correlation in logs
- Graceful fallback when OpenTelemetry not installed

### Configuration
```bash
OTEL_ENABLED=true                           # Enable/disable tracing
OTEL_SERVICE_NAME=my-service                # Service name in traces
OTEL_EXPORTER=otlp                          # otlp, console, zipkin, none
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # OTLP collector endpoint
OTEL_EXPORTER_ZIPKIN_ENDPOINT=http://localhost:9411/api/v2/spans  # Zipkin endpoint
OTEL_TRACES_SAMPLER_ARG=1.0                 # Sampling rate (0.0 to 1.0)
```

### Usage
```python
# Manual span creation
from app.core.tracing import create_span, set_span_attribute

with create_span("process_order", {"order_id": "123"}):
    set_span_attribute("customer_id", "456")
    # do work

# Function decorator
from app.core.tracing import trace_function

@trace_function("custom_operation", {"component": "orders"})
async def process_order(order_id: str):
    ...
```

---

## Phase 12.5 Complete - Enhanced Prometheus Metrics

### Files Created/Updated
- `app/core/metrics.py` - Enhanced with system, auth, WebSocket, webhook metrics
- `grafana/dashboards/api-overview.json` - API request metrics dashboard
- `grafana/dashboards/database-redis.json` - Database and cache metrics dashboard
- `grafana/dashboards/business-metrics.json` - Business, jobs, and AI metrics dashboard
- `grafana/README.md` - Dashboard installation guide
- `tests/unit/test_metrics.py` - 54 unit tests

### New Metrics

**System Metrics:**
- `process_memory_bytes{type}` - Process memory (rss, vms, shared)
- `process_cpu_seconds_total{mode}` - CPU time (user, system)
- `process_open_fds` - Open file descriptors
- `process_threads` - Thread count
- `app_uptime_seconds` - Application uptime
- `system_info` - Python version, platform info

**Authentication Metrics:**
- `auth_events_total{event,provider}` - Auth events (login, logout, signup, etc.)
- `auth_failures_total{reason}` - Auth failures by reason
- `token_operations_total{operation}` - Token ops (issued, verified, revoked)
- `active_sessions` - Active session count

**Rate Limiting Metrics:**
- `rate_limit_hits_total{endpoint,client_type}` - Rate limit blocks

**WebSocket Metrics:**
- `websocket_connections{status}` - Active connections
- `websocket_messages_total{direction,type}` - Message counts

**Webhook Metrics:**
- `webhook_events_total{provider,event_type,status}` - Webhook events
- `webhook_processing_duration_seconds{provider}` - Processing latency

### MetricsMiddleware
ASGI middleware for automatic request metrics collection:
```python
from app.core.metrics import MetricsMiddleware
app.add_middleware(MetricsMiddleware)
```

Features:
- Automatic request counting and latency tracking
- Path normalization (UUIDs/IDs → `{id}`)
- Skips health/metrics endpoints

### Grafana Dashboards
Three pre-built dashboards in `grafana/dashboards/`:
1. **API Overview** - Request rate, latency percentiles, error rates
2. **Database & Redis** - Connection pools, query performance, cache stats
3. **Business Metrics** - Users, subscriptions, background jobs, AI usage

### Usage
```python
from app.core.metrics import (
    record_auth_event,
    record_auth_failure,
    record_rate_limit_hit,
    record_websocket_connect,
    record_webhook_event,
    update_system_metrics,
)

# Record login
record_auth_event("login", provider="jwt")

# Record auth failure
record_auth_failure("expired_token")

# Record rate limit hit
record_rate_limit_hit("/api/v1/ai/chat", "user")

# Record webhook
record_webhook_event("stripe", "invoice.paid", "processed", duration=0.05)

# Update system metrics (call periodically)
update_system_metrics()
```

---

## Phase 12.6 Complete - Contact Form (Enhanced)

### Files Created
- `app/api/v1/public/contact.py` - Contact form endpoints
- `app/models/contact_submission.py` - ContactSubmission database model
- `migrations/versions/20260111_120000_add_contact_submission_model.py` - Migration
- `tests/unit/test_contact.py` - Unit tests (32 tests)

### New API Endpoints
- `POST /api/v1/public/contact` - Submit contact form
- `GET /api/v1/public/contact/status` - Check rate limit and config

### Fields
**Required:** name, email, message
**Optional:** subject, phone, company (configurable as required)
**Custom:** `extra_fields` dict for any additional data (budget, project_type, etc.)

### Features
- Modular fields with configurable requirements
- Custom fields via `extra_fields` dict
- Database persistence (ContactSubmission model)
- Confirmation email to sender
- Webhook for CRM/integrations (Zapier, Make, n8n compatible)
- Rate limiting (configurable)
- Honeypot + timing-based spam protection
- Source tracking for analytics

### Configuration
```bash
ADMIN_EMAIL=admin@example.com           # Admin notification email
CONTACT_REQUIRE_SUBJECT=false           # Make subject required
CONTACT_REQUIRE_PHONE=false             # Make phone required
CONTACT_SEND_CONFIRMATION=true          # Send confirmation to sender
CONTACT_WEBHOOK_URL=https://...         # Webhook for CRM integrations
CONTACT_RATE_LIMIT="5/hour"             # Rate limit per IP
```

---

## Phase 12.7 Complete - Usage-Based Billing

### Files Created
- `app/services/payments/usage.py` - UsageTracker and StripeUsageReporter services
- `app/models/usage_record.py` - UsageRecord model for PostgreSQL persistence
- `app/api/v1/admin/usage.py` - Admin usage analytics endpoints
- `app/api/v1/app/usage.py` - User usage endpoints
- `tests/unit/test_usage.py` - 32 unit tests

### Files Modified
- `app/core/middleware.py` - Added UsageTrackingMiddleware
- `app/api/v1/app/ai.py` - Added AI token tracking
- `app/api/v1/router.py` - Added usage routes
- `app/core/config.py` - Added usage tracking settings

### New API Endpoints

**User Endpoints:**
- `GET /api/v1/app/usage/summary` - Usage summary for all metrics
- `GET /api/v1/app/usage/current-period` - Current billing period usage
- `GET /api/v1/app/usage/trends` - Usage trends with growth rate
- `GET /api/v1/app/usage/daily` - Daily usage breakdown
- `GET /api/v1/app/usage/breakdown` - Usage by category (endpoint, model, etc.)
- `GET /api/v1/app/usage/metrics` - List available metrics

**Admin Endpoints:**
- `GET /api/v1/admin/usage/metrics` - List all metrics
- `GET /api/v1/admin/usage/summary/{user_id}` - User's usage summary
- `GET /api/v1/admin/usage/trends/{user_id}` - User's usage trends
- `GET /api/v1/admin/usage/daily/{user_id}` - User's daily usage
- `GET /api/v1/admin/usage/top-users` - Top users by metric
- `GET /api/v1/admin/usage/breakdown/{user_id}` - User's usage breakdown

### Usage Metrics
- `api_requests` - Total API requests
- `ai_tokens` - AI/LLM tokens consumed
- `ai_requests` - Number of AI completion requests
- `storage_bytes` - Storage space used
- `file_uploads` / `file_downloads` - File operations
- `websocket_messages` - WebSocket messages
- `background_jobs` - Background jobs executed
- `email_sent` - Emails sent

### Features
- Redis-based hot storage for current period counters
- In-memory fallback when Redis unavailable
- Automatic API request tracking via middleware
- AI token tracking with model breakdown
- Stripe usage reporting for metered billing
- Analytics: trends, growth rate, daily averages, peak detection
- Category breakdown (by endpoint, AI model, file type)

### Configuration
```bash
USAGE_TRACKING_ENABLED=true              # Enable/disable usage tracking
USAGE_TTL_DAYS=90                        # Days to keep usage data
USAGE_STRIPE_SYNC_ENABLED=false          # Enable Stripe reporting
USAGE_STRIPE_SYNC_INTERVAL=3600          # Sync interval in seconds
```

### Usage Examples
```python
# Track API request (automatic via middleware)
# Tracked automatically for authenticated requests

# Track AI usage (in AI endpoints)
from app.services.payments.usage import track_ai_usage
await track_ai_usage(
    user_id="user123",
    model="gpt-4o",
    prompt_tokens=100,
    completion_tokens=200,
)

# Get usage tracker
from app.services.payments.usage import get_usage_tracker
tracker = get_usage_tracker()

# Get usage summary
summary = await tracker.get_usage(
    user_id="user123",
    metric=UsageMetric.API_REQUESTS,
    period_start=start_of_month,
    period_end=now
)

# Get trends
trend = await tracker.get_trends("user123", UsageMetric.AI_TOKENS)
print(f"Growth: {trend.growth_rate}%")
```

---

## Phase 12.8 Complete - SQLite Fallback

### Files Created
- `app/models/compat.py` - Cross-database compatibility utilities:
  - `JSONColumn()` - JSONB for PostgreSQL, JSON for SQLite
  - `ArrayColumn()` - ARRAY for PostgreSQL, JSON for SQLite
  - `JSONEncodedList`, `JSONEncodedDict` - TypeDecorator helpers
- `tests/unit/test_sqlite_fallback.py` - 33 unit tests

### Files Modified
- `app/core/config.py` - Added SQLite detection and default:
  - `DATABASE_URL` defaults to SQLite if not set
  - `is_sqlite` computed property for database detection
  - Updated `async_database_url` to handle SQLite driver
- `app/core/db.py` - SQLite-compatible engine configuration:
  - `StaticPool` for SQLite (required for aiosqlite)
  - `check_same_thread=False` for multi-threaded access
- `app/core/cache.py` - In-memory cache fallback:
  - `InMemoryCache` class with TTL support
  - Hash and set operations for Redis compatibility
  - `get_cache()` returns Redis or in-memory fallback

### Features
- Run without Docker/PostgreSQL/Redis
- SQLite for database (file-based, no server needed)
- In-memory cache when Redis unavailable
- Automatic driver detection and configuration
- Compatible with existing models

### Usage

**Offline Development (no Docker):**
```bash
# Set SQLite in .env
DATABASE_URL="sqlite+aiosqlite:///./dev.db"
# Leave REDIS_URL empty for in-memory cache

# Run the app
make dev
```

**Standard Development (with Docker):**
```bash
make up   # Start PostgreSQL + Redis
make dev  # Run app
```

---

## Phase 12 Complete - All Features

### Completed
- ✅ **12.1 API Versioning** - v1/v2 routing, deprecation headers, version middleware
- ✅ **12.2 WebSocket Support** - Real-time communication
- ✅ **12.3 Admin Dashboard** - Stats, feature flags, impersonation, audit logs
- ✅ **12.4 OpenTelemetry** - Distributed tracing with OTLP/Zipkin export, log correlation
- ✅ **12.5 Enhanced Metrics** - System/auth/WebSocket/webhook metrics, Grafana dashboards
- ✅ **12.6 Contact Form** - Public endpoint with spam protection
- ✅ **12.7 Usage-Based Billing** - Track API/AI/storage usage, Stripe reporting, analytics
- ✅ **12.8 SQLite Fallback** - Offline development with SQLite and in-memory cache

### Note

Phase 12 is complete. All v1.1 features are now implemented.

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
│   │   ├── middleware.py       # Rate limiting, security headers, logging
│   │   ├── sentry.py           # Sentry error tracking
│   │   ├── metrics.py          # Prometheus metrics
│   │   └── logging.py          # Structured logging
│   ├── models/                 # SQLModel models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # External services (ai, email, storage, websocket)
│   │   ├── email/              # Email providers (Resend, SendGrid, Console)
│   │   ├── storage/            # Storage providers (S3, R2, Cloudinary, Local)
│   │   ├── ai/                 # AI providers (OpenAI, Anthropic, Gemini)
│   │   └── websocket/          # WebSocket connection manager (Phase 12)
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
├── scripts/
│   └── migrate_production.py   # Production migration tool
├── documentation/              # User-facing documentation
│   ├── API-REFERENCE.md        # Complete API docs
│   ├── ARCHITECTURE.md         # System design
│   ├── CONTRIBUTING.md         # Contribution guide
│   ├── FRONTEND-INTEGRATION.md # Client integration
│   ├── GETTING-STARTED.md      # Setup guide
│   └── MODULAR-GUIDE.md        # Component selection
├── docs/                       # Internal documentation
│   ├── implementation/         # Phase checklists
│   ├── audit/                  # Progress tracking
│   ├── omnistack-technical-prd.md  # Code examples
│   ├── DEPLOYMENT.md           # Deployment guide
│   └── BACKUP.md               # Backup & recovery guide
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI pipeline
│       ├── deploy.yml          # Deployment pipeline
│       └── security.yml        # Security scans
├── railway.toml                # Railway config
├── render.yaml                 # Render config
├── fly.toml                    # Fly.io config
├── .env.example
├── pyproject.toml
├── Makefile
└── README.md
```

---

## Documentation References

### User Documentation (`documentation/`)

| Document | Best For |
|----------|----------|
| [Getting Started](documentation/GETTING-STARTED.md) | New developers, setup |
| [API Reference](documentation/API-REFERENCE.md) | Frontend developers |
| [Architecture](documentation/ARCHITECTURE.md) | Backend developers |
| [Modular Guide](documentation/MODULAR-GUIDE.md) | Customizing the boilerplate |
| [Frontend Integration](documentation/FRONTEND-INTEGRATION.md) | Frontend/Mobile developers |
| [Contributing](documentation/CONTRIBUTING.md) | Contributors |

### Internal Documentation (`docs/`)

| Document | Purpose |
|----------|---------|
| `docs/omnistack-technical-prd.md` | Code examples for all features |
| `docs/implementation/MASTER-TRACKER.md` | All 123 tasks overview |
| `docs/audit/AUDIT-SUMMARY.md` | Detailed progress tracking |
| `docs/DEPLOYMENT.md` | Deployment guide |
| `docs/BACKUP.md` | Backup & recovery guide |

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

*Last Updated: 2026-01-11*
*v1.0 Complete - All 11 Core Phases Finished*
*v1.1 In Progress - Phase 12.2 (WebSocket), 12.3 (Admin Dashboard), 12.6 (Contact Form) Complete*
*Documentation: https://simanam.github.io/omni-stack-backend-boilerplate-fastapi/*
