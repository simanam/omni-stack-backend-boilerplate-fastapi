# Development Changelog

**Project:** OmniStack Backend Boilerplate
**Purpose:** Track all changes made during development

---

## Format

Each entry follows this format:

```
## [Date] - Phase X.Y Task Name

### Added
- New files or features

### Changed
- Modifications to existing files

### Fixed
- Bug fixes

### Removed
- Deleted files or features

### Technical Notes
- Implementation details
- Design decisions
- Dependencies added
```

---

## [Unreleased]

### Planning Phase

#### 2026-01-10 - Project Planning

**Added:**
- `docs/implementation/phase-1-foundation.md` - Foundation checklist
- `docs/implementation/phase-2-authentication.md` - Auth checklist
- `docs/implementation/phase-3-crud-patterns.md` - CRUD checklist
- `docs/implementation/phase-4-middleware-security.md` - Security checklist
- `docs/implementation/phase-5-background-jobs.md` - Jobs checklist
- `docs/implementation/phase-6-external-services.md` - Services checklist
- `docs/implementation/phase-7-ai-gateway.md` - AI checklist
- `docs/implementation/phase-8-payments.md` - Payments checklist
- `docs/implementation/phase-9-testing.md` - Testing checklist
- `docs/implementation/phase-10-deployment.md` - Deployment checklist
- `docs/implementation/phase-11-documentation.md` - Docs checklist
- `docs/implementation/phase-12-advanced-features.md` - v1.1 features
- `docs/implementation/MASTER-TRACKER.md` - Central tracking
- `docs/audit/ERROR-TRACKER.md` - Issue tracking
- `docs/audit/AUDIT-SUMMARY.md` - Progress summary
- `docs/audit/CHANGELOG.md` - This file

**Technical Notes:**
- 12 phases planned (11 core + 1 enhancement)
- 124 total tasks identified
- v1.0 requires 116 tasks
- v1.1 adds 8 optional tasks

---

## Phase 1: Foundation

*Not started*

---

## Phase 2: Authentication

*Not started*

---

## Phase 3: CRUD Patterns

*Not started*

---

## Phase 4: Middleware & Security

#### 2026-01-11 - Phase 4 Complete

**Added:**
- `app/core/middleware.py` - All middleware components:
  - `RateLimitConfig` - Parse rate limit strings (60/minute)
  - `RateLimiter` - Sliding window with Redis/memory fallback
  - `RateLimitMiddleware` - Route-based rate limiting
  - `SecurityHeadersMiddleware` - OWASP security headers
  - `RequestIDMiddleware` - UUID per request, contextvars
  - `RequestLoggingMiddleware` - Request/response logging
  - `register_middleware()` - Helper to register all middleware
- `app/utils/validators.py` - Input validation:
  - `ValidatedEmail`, `ValidatedURL`, `ValidatedUUID` - Pydantic types
  - `SanitizedString`, `PlainTextString` - XSS prevention
  - `SafePath` - Path traversal prevention
  - `max_length()`, `min_length()` - String length validators
  - `is_valid_image()`, `is_valid_document()` - File type validation
- `app/utils/crypto.py` - Cryptographic utilities:
  - `generate_token()`, `generate_urlsafe_token()` - Random tokens
  - `generate_api_key()` - API key generation with prefix
  - `compute_hmac()`, `verify_hmac()` - HMAC signing
  - `verify_webhook_signature()` - Webhook verification
  - `hash_password()`, `verify_password()` - PBKDF2-SHA256
  - `hash_sha256()`, `hash_sha512()` - Hash utilities
- `app/utils/resilience.py` - Resilience patterns:
  - `CircuitBreaker` - Circuit breaker with CLOSED/OPEN/HALF_OPEN
  - `get_circuit_breaker()` - Named circuit breaker registry
  - `retry_async()`, `@with_retry` - Exponential backoff retry
  - `with_timeout()`, `@timeout` - Async timeout decorator
  - `with_fallback()` - Fallback on failure
  - `resilient_call()` - Combined resilience patterns
- `tests/unit/test_middleware.py` - 16 middleware tests

**Changed:**
- `app/main.py` - Added middleware registration, exposed rate limit headers in CORS

**Technical Notes:**
- Middleware execution order: RequestID → Logging → Security → RateLimit
- Rate limiting uses sorted sets in Redis for sliding window
- Circuit breaker uses dataclass with asyncio.Lock for state
- Python 3.12 type parameters used for generic functions
- HSTS only added in production environment

---

## Phase 5: Background Jobs

*Not started*

---

## Phase 6: External Services

*Not started*

---

## Phase 7: AI Gateway

#### 2026-01-10 - Phase 7 Complete

**Added:**
- `app/services/ai/__init__.py` - Module exports
- `app/services/ai/base.py` - LLM interface:
  - `Role` enum (SYSTEM, USER, ASSISTANT)
  - `ModelComplexity` enum (SIMPLE, MODERATE, COMPLEX, SEARCH)
  - `Message` dataclass for chat messages
  - `LLMResponse` dataclass (content, model, provider, usage, finish_reason, latency_ms)
  - `BaseLLMProvider` abstract class with complete(), stream(), complete_simple(), stream_simple()
- `app/services/ai/openai_provider.py` - OpenAI implementation:
  - `OpenAIProvider` class using AsyncOpenAI
  - Default model: gpt-4o
  - Lazy client initialization
  - Streaming support with async generator
- `app/services/ai/anthropic_provider.py` - Anthropic implementation:
  - `AnthropicProvider` class using AsyncAnthropic
  - Default model: claude-sonnet-4-5-20250929
  - System message handling (separate from messages array)
  - Streaming via client.messages.stream() and text_stream
- `app/services/ai/gemini_provider.py` - Google Gemini implementation:
  - `GeminiProvider` class using google-genai Client
  - Default model: gemini-2.5-flash
  - Role conversion (assistant → model, system → system_instruction)
  - Async streaming via generate_content_stream
- `app/services/ai/factory.py` - Provider factory:
  - `get_llm_provider()` with @lru_cache
  - `get_available_providers()` - List configured providers
  - `is_ai_available()` - Check if any provider configured
  - `clear_llm_cache()` - Clear cache for testing
- `app/services/ai/router.py` - Smart routing:
  - `ModelRoute` dataclass (provider, model, cost_per_1k_tokens)
  - `MODEL_ROUTES` mapping complexity → optimal model
  - `LLMRouter` class with complete() and chat() methods
  - `get_llm_router()` singleton getter
  - Routing: SIMPLE→gpt-4o-mini, MODERATE→gpt-4o, COMPLEX→claude-sonnet-4-5
- `app/schemas/ai.py` - AI schemas:
  - `ChatMessage`, `CompletionRequest`, `SimpleCompletionRequest`
  - `RoutedCompletionRequest`, `CompletionResponse`, `AIStatusResponse`
- `app/api/v1/app/ai.py` - AI endpoints:
  - `GET /api/v1/app/ai/status` - AI service status
  - `POST /api/v1/app/ai/completions` - Chat completion with streaming
  - `POST /api/v1/app/ai/chat` - Simple prompt-based chat
  - `POST /api/v1/app/ai/chat/routed` - Smart routed by complexity

**Changed:**
- `app/core/config.py` - Added AI settings:
  - `AI_DEFAULT_PROVIDER`: openai | anthropic | gemini
  - `AI_DEFAULT_MODEL`: default model name
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- `app/core/exceptions.py` - Added `ServiceUnavailableError`
- `app/api/v1/router.py` - Added AI router
- `.env.example` - Added AI provider configuration

**Technical Notes:**
- All providers use lazy client initialization
- Streaming uses Server-Sent Events (SSE) format
- Token usage tracked in LLMResponse.usage dict
- Cost estimates in ModelRoute.cost_per_1k_tokens
- Admin usage dashboard and prompt templates deferred to v1.1

---

## Phase 8: Payments & Webhooks

*Not started*

---

## Phase 9: Testing

*Not started*

---

## Phase 10: Deployment

*Not started*

---

## Phase 11: Documentation

*Not started*

---

## Phase 12: Advanced Features

#### 2026-01-11 - Phase 12.1 API Versioning Complete

**Added:**
- `app/core/versioning.py` - Version utilities:
  - `APIVersion` enum (V1, V2) with parsing from various formats
  - `get_version_from_path()` - Extract version from URL `/api/v1/...`
  - `get_version_from_header()` - Support Accept-Version, X-API-Version headers
  - `VersionInfo` dataclass for deprecation metadata
  - `add_version_headers()` - RFC 8594 compliant response headers
  - `VersionMiddleware` - Auto-add version headers to responses
- `app/api/v2/__init__.py` - Version 2 package initialization
- `app/api/v2/router.py` - v2 router aggregation
- `app/api/v2/public/__init__.py` - v2 public endpoints package
- `app/api/v2/public/health.py` - Enhanced health endpoints with uptime and latency
- `app/api/v2/app/__init__.py` - v2 app endpoints package
- `app/api/v2/app/users.py` - User endpoints with metadata wrapper response
- `tests/unit/test_versioning.py` - 38 unit tests for versioning

**Changed:**
- `app/main.py` - Added v2 router and version middleware registration
- `app/core/config.py` - Added `API_V2_STR` configuration

**Technical Notes:**
- Version detection: path-based (primary), header-based (fallback)
- Response headers: `X-API-Version`, `X-API-Latest-Version`
- Deprecation headers: `Deprecation`, `Sunset`, `X-Deprecation-Notice`, `Link`
- v2 response format wraps data with metadata (request_id, timestamp, version)

---

#### 2026-01-11 - Phase 12.2 WebSocket Support Complete

**Added:**
- `app/services/websocket/__init__.py` - Package exports
- `app/services/websocket/manager.py` - Connection manager:
  - `WebSocketManager` class with Redis pub/sub
  - Connection tracking by user ID
  - Channel/room subscriptions
  - Broadcast to users, channels, or all
  - Presence tracking (online users)
  - Heartbeat/ping-pong support
- `app/services/websocket/events.py` - Event types:
  - `WebSocketEventType` enum (CONNECT, DISCONNECT, MESSAGE, etc.)
  - `WebSocketMessage` schema for structured messages
- `app/api/v1/app/ws.py` - WebSocket endpoints:
  - `ws://host/api/v1/app/ws?token=<jwt>` - WebSocket connection
  - `GET /api/v1/app/ws/status` - Connection statistics
- `tests/unit/test_websocket.py` - 23 unit tests

**Changed:**
- `app/api/v1/router.py` - Added WebSocket router

**Technical Notes:**
- JWT authentication via query parameter (browsers can't set headers for WS)
- Redis pub/sub enables multi-instance communication
- Graceful degradation when Redis unavailable (single-instance mode)

---

#### 2026-01-11 - Phase 12.3 Admin Dashboard Complete

**Added:**
- `app/models/audit_log.py` - Audit log model:
  - Tracks actor, action, resource, changes
  - IP address and user agent capture
  - JSONB for previous/new values
- `app/models/feature_flag.py` - Feature flag model:
  - Types: boolean, percentage, user_list, plan_based
  - Enabled users list, allowed plans
  - Expiration date support
- `app/api/v1/admin/dashboard.py` - Dashboard endpoints:
  - `GET /dashboard/stats` - System statistics
  - `GET /dashboard/audit-logs` - Audit log listing
  - `GET /dashboard/audit-logs/{id}` - Get audit log by ID
- `app/api/v1/admin/feature_flags.py` - Feature flags CRUD:
  - Full CRUD operations for feature flags
  - Enable/disable, add/remove user
  - Check flag status for specific user
- `app/api/v1/admin/impersonate.py` - User impersonation:
  - Start/stop impersonation with audit logging
  - List active impersonations
  - Role-based restrictions (can't impersonate higher roles)
- `migrations/versions/20260111_100000_add_audit_log_and_feature_flag_models.py`
- `tests/unit/test_admin_dashboard.py` - 31 unit tests

**Changed:**
- `app/api/v1/admin/__init__.py` - Added dashboard, feature_flags, impersonate routers

**Technical Notes:**
- Feature flag evaluation uses consistent hashing for percentage rollouts
- Impersonation creates special JWT with original_user_id claim
- Audit logs capture before/after state for changes

---

#### 2026-01-11 - Phase 12.4 OpenTelemetry Tracing Complete

**Added:**
- `app/core/tracing.py` - OpenTelemetry integration:
  - `init_tracing()` - Initialize with configurable exporters
  - `instrument_app()` - FastAPI auto-instrumentation
  - `instrument_sqlalchemy()` - Database query tracing
  - `instrument_redis()` - Redis operation tracing
  - `instrument_httpx()` - External HTTP call tracing
  - `create_span()` - Manual span creation context manager
  - `trace_function()` - Decorator for function tracing
  - `get_current_trace_id()`, `get_current_span_id()` - Context access
  - `set_span_attribute()`, `set_span_status()`, `record_exception()` - Span helpers
  - `_NoOpTracer`, `_NoOpSpan`, `_NoOpSpanContext` - Graceful fallback
  - `shutdown_tracing()` - Clean shutdown
- `tests/unit/test_tracing.py` - 38 unit tests

**Changed:**
- `app/core/config.py` - Added OpenTelemetry configuration:
  - `OTEL_ENABLED`, `OTEL_SERVICE_NAME`
  - `OTEL_EXPORTER` (otlp, console, zipkin, none)
  - `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_ZIPKIN_ENDPOINT`
  - `OTEL_TRACES_SAMPLER_ARG` (sampling rate 0.0-1.0)
- `app/main.py` - Integrated tracing initialization and instrumentation
- `app/core/logging.py` - Added trace context to log output (trace_id, span_id)
- `pyproject.toml` - Added `tracing` optional dependency group
- `.env.example` - Added OTEL configuration section

**Technical Notes:**
- Graceful fallback: works without OpenTelemetry installed (NoOp implementations)
- Auto-instrumentation: FastAPI, SQLAlchemy, Redis, httpx
- Exporters: OTLP (Jaeger, Tempo), Zipkin, Console (dev)
- W3C Trace Context propagation for distributed tracing
- Log correlation: trace_id and span_id automatically added to JSON logs

---

#### 2026-01-11 - Phase 12.6 Contact Form Complete

**Added:**
- `app/api/v1/public/contact.py` - Contact form endpoints:
  - `POST /contact` - Submit contact form
  - `GET /contact/status` - Check rate limit and config
- `app/models/contact_submission.py` - ContactSubmission model:
  - Required: name, email, message
  - Optional: subject, phone, company (configurable as required)
  - Custom: extra_fields dict for additional data
  - Source tracking, admin notification, confirmation email
- `migrations/versions/20260111_120000_add_contact_submission_model.py`
- `tests/unit/test_contact.py` - 32 unit tests

**Changed:**
- `app/core/config.py` - Added contact form configuration:
  - `CONTACT_REQUIRE_SUBJECT`, `CONTACT_REQUIRE_PHONE`
  - `CONTACT_SEND_CONFIRMATION`, `CONTACT_WEBHOOK_URL`
  - `CONTACT_RATE_LIMIT`, `ADMIN_EMAIL`
- `app/api/v1/router.py` - Added contact router

**Technical Notes:**
- Spam protection: honeypot field + timing-based bot detection
- Rate limiting: configurable per IP (default: 5/hour)
- Webhooks: generic URL with HMAC signature (Zapier/Make/n8n compatible)
- Confirmation emails: sent to sender with reference number

---

#### 2026-01-11 - Phase 12.5 Enhanced Metrics Complete

**Added:**
- `app/core/metrics.py` - Enhanced with comprehensive metrics:
  - System metrics: `process_memory_bytes`, `process_cpu_seconds_total`, `process_open_fds`, `process_threads`, `app_uptime_seconds`, `system_info`
  - Authentication metrics: `auth_events_total`, `auth_failures_total`, `token_operations_total`, `active_sessions`
  - Rate limiting metrics: `rate_limit_hits_total`
  - WebSocket metrics: `websocket_connections`, `websocket_messages_total`
  - Webhook metrics: `webhook_events_total`, `webhook_processing_duration_seconds`
  - `MetricsMiddleware` - ASGI middleware for automatic HTTP request tracking
  - `update_system_metrics()` - Periodic system metrics collection
  - `collect_metrics_snapshot()` - Health check snapshot
  - `init_metrics()` - Initialization function
- `grafana/dashboards/api-overview.json` - API metrics dashboard:
  - Request rate, P95 latency, error rate, requests in progress
  - Request rate by method, latency percentiles
  - Request rate by status code, top endpoints
- `grafana/dashboards/database-redis.json` - Database/cache dashboard:
  - Active connections, query latency, error rate
  - Connection pool status, queries by operation
  - Cache hit rate, Redis connections
- `grafana/dashboards/business-metrics.json` - Business KPIs dashboard:
  - Users, subscriptions by plan, daily signups
  - Background jobs queue, completion rate, duration
  - LLM requests, token usage, latency by provider
- `grafana/README.md` - Dashboard installation guide:
  - Import instructions, provisioning config
  - Docker Compose setup, variables, alerts
- `tests/unit/test_metrics.py` - 54 unit tests:
  - Request, database, cache, job metrics
  - System, auth, rate limit, WebSocket, webhook metrics
  - MetricsMiddleware, path normalization
  - Metrics snapshot, initialization

**Technical Notes:**
- MetricsMiddleware normalizes paths (UUIDs/numeric IDs → `{id}`)
- System metrics use `/proc/self/status` on Linux, `resource` module on macOS
- All metrics have graceful fallback when prometheus_client not installed
- Grafana dashboards use Prometheus datasource with configurable job filter
- Dashboard provisioning supported via YAML config files

---

#### 2026-01-11 - Phase 12.8 SQLite Fallback Complete

**Added:**
- `app/models/compat.py` - Cross-database compatibility utilities:
  - `JSONColumn()` - JSONB for PostgreSQL, JSON for SQLite
  - `ArrayColumn()` - ARRAY for PostgreSQL, JSON for SQLite
  - `JSONEncodedList`, `JSONEncodedDict` - TypeDecorators for JSON encoding
  - `get_json_type()`, `get_array_type()` - Type getters for current database
- `tests/unit/test_sqlite_fallback.py` - 33 unit tests for SQLite fallback

**Changed:**
- `app/core/config.py` - Added SQLite support:
  - Default `DATABASE_URL` to SQLite for offline development
  - `is_sqlite` computed property for database detection
  - Updated `async_database_url` to handle `sqlite://` → `sqlite+aiosqlite://`
- `app/core/db.py` - SQLite-compatible engine configuration:
  - Added `StaticPool` for SQLite connections
  - Added `check_same_thread=False` for aiosqlite
- `app/core/cache.py` - Enhanced in-memory cache fallback:
  - Full `InMemoryCache` class with TTL support
  - Hash operations: `hset`, `hget`, `hgetall`, `hincrby`, `hdel`
  - Set operations: `sadd`, `smembers`, `srem`, `scard`
  - Key scanning: `keys()` with prefix matching
  - `get_cache()` function for unified cache access
- `.env.example` - Added SQLite and in-memory cache documentation

**Technical Notes:**
- SQLite uses `aiosqlite` driver for async compatibility
- `StaticPool` required for SQLite to prevent connection issues
- In-memory cache provides Redis-compatible API for offline development
- Cross-database compatibility layer allows models to work with both PostgreSQL and SQLite
- No schema changes required - uses JSON fallback for JSONB and ARRAY types

---

#### 2026-01-11 - Phase 12.7 Usage-Based Billing Complete

**Added:**
- `app/services/payments/usage.py` - Usage tracking service:
  - `UsageMetric` enum: API_REQUESTS, AI_TOKENS, AI_REQUESTS, STORAGE_BYTES, etc.
  - `UsageEvent`, `UsageSummary`, `UsageTrend` dataclasses
  - `UsageTracker` class with Redis storage and in-memory fallback
  - `StripeUsageReporter` for metered billing integration
  - Convenience functions: `track_api_request()`, `track_ai_usage()`, `track_storage()`
  - `get_usage_tracker()`, `get_stripe_usage_reporter()` singletons
- `app/models/usage_record.py` - Usage record model:
  - `UsageRecord` SQLModel for PostgreSQL persistence
  - `UsageSummaryView`, `UsageAnalytics`, `UserUsageOverview` view models
  - Indexes for user_id, metric, period lookups
- `app/api/v1/admin/usage.py` - Admin usage endpoints:
  - `GET /usage/metrics` - List available metrics
  - `GET /usage/summary/{user_id}` - User's usage summary
  - `GET /usage/trends/{user_id}` - Usage trends with growth rate
  - `GET /usage/daily/{user_id}` - Daily usage breakdown
  - `GET /usage/top-users` - Top users by metric
  - `GET /usage/breakdown/{user_id}` - Usage by category
- `app/api/v1/app/usage.py` - User usage endpoints:
  - `GET /usage/summary` - Own usage summary
  - `GET /usage/current-period` - Current billing period usage
  - `GET /usage/trends` - Usage trends
  - `GET /usage/daily` - Daily usage
  - `GET /usage/breakdown` - Usage by category
  - `GET /usage/metrics` - List available metrics
- `tests/unit/test_usage.py` - 32 unit tests

**Changed:**
- `app/core/middleware.py` - Added `UsageTrackingMiddleware`:
  - Automatic API request tracking for authenticated users
  - Skips health and public endpoints
  - Extracts user_id from JWT token
- `app/api/v1/app/ai.py` - Added AI usage tracking:
  - `_track_ai_usage()` helper function
  - Tracks prompt tokens, completion tokens, model used
- `app/api/v1/router.py` - Added usage routes for admin and app
- `app/services/payments/__init__.py` - Exported usage tracking functions
- `app/core/config.py` - Added usage tracking configuration:
  - `USAGE_TRACKING_ENABLED`, `USAGE_TTL_DAYS`
  - `USAGE_STRIPE_SYNC_ENABLED`, `USAGE_STRIPE_SYNC_INTERVAL`
- `.env.example` - Added usage tracking environment variables

**Technical Notes:**
- Redis-based hot storage with `usage:{user_id}:{metric}:{period}` key pattern
- In-memory fallback dictionary when Redis unavailable
- Category breakdown stored in hash: endpoint for API, model for AI, file type for storage
- Stripe SDK v14 compatibility: uses raw API for legacy usage records
- Trend analysis: calculates growth rate, daily average, peak detection
- TTL: usage data expires after configurable days (default: 90)

---

#### 2026-01-11 - Documentation Updates

**Updated:**
- `documentation/API-REFERENCE.md` - Added Usage Endpoints section:
  - User endpoints: summary, current-period, trends, daily, breakdown, metrics
  - Admin endpoints: metrics, summary, trends, daily, top-users, breakdown
- `documentation/GETTING-STARTED.md`:
  - Added "Option B: Without Docker (SQLite Fallback)" quick start
  - Added Usage Tracking configuration section
- `documentation/ARCHITECTURE.md`:
  - Added Usage Tracking flow diagram and metrics table
  - Added Database Compatibility section for SQLite fallback
- `documentation/MODULAR-GUIDE.md`:
  - Added Usage Tracking to optional components table
  - Added "Remove Usage Tracking" section with removal steps
- `documentation/FRONTEND-INTEGRATION.md`:
  - Added Usage TypeScript interfaces (UsageSummary, UsageTrend, etc.)
  - Added Query Keys for TanStack Query
  - Added UsageDashboard React component example

**Changed:**
- `.gitignore` - Added `docs/` exclusion for internal documentation
- Separated internal docs (`docs/`) from user docs (`documentation/`)

**Technical Notes:**
- Internal documentation moved to separate `docs-internal` branch
- User-facing documentation deployed to GitHub Pages
- `docs/` folder not tracked in `main` or `feature/phase-12-advanced` branches

---

## Release History

### v1.0.0 (Complete)

**Released:** 2026-01-10

**Features:**
- Universal authentication (Supabase, Clerk, Custom OAuth)
- Async database with SQLModel + Alembic
- Redis-backed rate limiting
- Background jobs with ARQ
- Multi-provider AI gateway
- Email service (Resend, SendGrid)
- File storage (S3, R2)
- Stripe payments + webhooks
- Health checks + monitoring
- Docker + deployment configs

**Test Coverage:** 190+ tests passing

---

### v1.1.0 (Complete)

**Released:** 2026-01-11

**Features:**
- ✅ API versioning (v1/v2) with deprecation headers
- ✅ WebSocket support with Redis pub/sub
- ✅ Admin dashboard endpoints (stats, audit logs)
- ✅ Feature flags (boolean, percentage, user_list, plan_based)
- ✅ OpenTelemetry tracing (OTLP, Zipkin, Console exporters)
- ✅ Enhanced Prometheus metrics (system, auth, WebSocket, webhook)
- ✅ Grafana dashboards (API, Database, Business)
- ✅ Contact form with spam protection
- ✅ Usage-based billing (API/AI/storage tracking, Stripe reporting, analytics)
- ✅ SQLite fallback (offline development)

**Test Coverage:** 430+ tests passing

---

## Migration Notes

*No migrations yet*

---

## Breaking Changes

*No breaking changes yet*

---

*Last Updated: 2026-01-11*
