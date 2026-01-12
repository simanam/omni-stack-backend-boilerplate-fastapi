# Phase 12: Advanced Features (v1.1)

**Duration:** Enhancement phase
**Goal:** Add Tier 2 features - WebSocket, API versioning, admin dashboard, observability

**Prerequisites:** Phase 1-11 completed (Core v1.0)

**Note:** This phase is optional for v1.0 but recommended for production SaaS

---

## 12.1 API Versioning Strategy ✅

### Files created:
- [x] `app/api/v2/__init__.py` — Version 2 package
- [x] `app/api/v2/router.py` — v2 router aggregation
- [x] `app/api/v2/public/health.py` — Enhanced v2 health endpoints
- [x] `app/api/v2/app/users.py` — v2 user endpoints with metadata wrapper
- [x] `app/core/versioning.py` — Version utilities (enum, detection, middleware)
- [x] `tests/unit/test_versioning.py` — Unit tests (38 tests)

### Checklist:
- [x] `/api/v1/...` and `/api/v2/...` routing structure
- [x] Version-specific routers
- [x] Deprecation headers for old endpoints (RFC 8594)
- [x] Version detection from header (Accept-Version, X-API-Version)
- [x] Version-specific middleware (VersionMiddleware)
- [x] Sunset header for deprecated endpoints
- [x] Documentation per version

### Features:
- **APIVersion enum**: V1, V2 with parsing from various formats
- **Path-based detection**: Extract version from URL `/api/v1/...`
- **Header-based detection**: `Accept-Version` or `X-API-Version` headers
- **Response headers**: `X-API-Version`, `X-API-Latest-Version`
- **Deprecation headers**: `Deprecation`, `Sunset`, `X-Deprecation-Notice`, `Link`
- **v2 enhancements**: Metadata wrapper, request_id, uptime, latency metrics

### v2 Response Format:
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

### Validation:
- [x] Both v1 and v2 routes work
- [x] Deprecation warnings visible (when version is deprecated)

---

## 12.2 WebSocket Support ✅

### Files created:
- [x] `app/api/v1/app/ws.py` — WebSocket endpoints
- [x] `app/services/websocket/__init__.py`
- [x] `app/services/websocket/manager.py` — Connection manager
- [x] `app/services/websocket/events.py` — Event types
- [x] `tests/unit/test_websocket.py` — Unit tests (23 tests)

### Checklist:
- [x] WebSocket connection manager:
  - [x] Track active connections by user
  - [x] Broadcast to specific users
  - [x] Broadcast to all connections
  - [x] Room/channel support
- [x] Authentication for WebSocket:
  - [x] Token in query param or first message
  - [x] Verify JWT on connect
- [x] Real-time notifications:
  - [x] Push notifications to connected clients
  - [x] Integration with background jobs
- [x] Live updates:
  - [x] Dashboard real-time data
  - [x] Activity feeds
- [x] Connection management:
  - [x] Heartbeat/ping-pong
  - [x] Graceful disconnect
  - [x] Reconnection handling
- [x] Redis pub/sub for multi-instance support

### Validation:
- [x] WebSocket connects with auth
- [x] Messages broadcast correctly
- [x] Works across multiple server instances

---

## 12.3 Admin Dashboard Endpoints ✅

### Files created:
- [x] `app/api/v1/admin/dashboard.py` — Dashboard stats
- [x] `app/api/v1/admin/feature_flags.py` — Feature flags CRUD
- [x] `app/api/v1/admin/impersonate.py` — User impersonation
- [x] `app/models/feature_flag.py` — Feature flag model
- [x] `app/models/audit_log.py` — Audit log model
- [x] `migrations/versions/20260111_100000_add_audit_log_and_feature_flag_models.py` — Migration
- [x] `tests/unit/test_admin_dashboard.py` — Unit tests (31 tests)

### Checklist:
- [x] User management:
  - [x] List all users with pagination/search (existing in admin/users.py)
  - [x] User details view (existing in admin/users.py)
  - [x] Update user role/status (existing in admin/users.py)
  - [x] Impersonate user (for debugging)
- [x] Feature flags:
  - [x] Create/update/delete flags
  - [x] Enable per user/percentage
  - [x] Check flag status
  - [x] Plan-based flags
  - [x] Expiration support
- [x] System metrics:
  - [x] Active users count
  - [x] User growth stats
  - [x] Subscription stats
  - [x] Background job stats
- [x] Webhook logs:
  - [x] View webhook history (dashboard stats)
- [x] Audit log:
  - [x] Track admin actions
  - [x] Who did what when
  - [x] Filter by actor, action, resource

### Validation:
- [x] Admin endpoints secured (require_admin dependency)
- [x] Feature flags work (boolean, percentage, user_list, plan_based)
- [x] Impersonation works safely (audit logged, role restrictions)

---

## 12.4 OpenTelemetry / Distributed Tracing ✅

### Files created:
- [x] `app/core/tracing.py` — OpenTelemetry setup
- [x] `tests/unit/test_tracing.py` — Unit tests (38 tests)

### Checklist:
- [x] OpenTelemetry SDK integration
- [x] Trace context propagation (W3C Trace Context)
- [x] Span creation for:
  - [x] HTTP requests (FastAPI instrumentation)
  - [x] Database queries (SQLAlchemy instrumentation)
  - [x] External API calls (httpx instrumentation)
  - [x] Redis operations (Redis instrumentation)
  - [x] Custom spans via `create_span()` and `@trace_function`
- [x] Export to:
  - [x] OTLP (Jaeger, Tempo, etc.)
  - [x] Zipkin
  - [x] Console (for development)
- [x] Correlation with logs (trace ID in logs)
- [x] Custom attributes on spans

### Features:
- **Auto-instrumentation**: FastAPI, SQLAlchemy, Redis, httpx
- **Manual tracing**: `create_span()` context manager, `@trace_function` decorator
- **Span attributes**: `set_span_attribute()`, `set_span_status()`, `record_exception()`
- **Trace context**: `get_current_trace_id()`, `get_current_span_id()`
- **Log correlation**: Trace ID and span ID automatically added to JSON logs
- **Graceful fallback**: Works without OpenTelemetry installed (NoOp implementations)

### Configuration:
```bash
OTEL_ENABLED=true                           # Enable/disable tracing
OTEL_SERVICE_NAME=my-service                # Service name in traces
OTEL_EXPORTER=otlp                          # otlp, console, zipkin, none
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # OTLP collector endpoint
OTEL_EXPORTER_ZIPKIN_ENDPOINT=http://localhost:9411/api/v2/spans  # Zipkin endpoint
OTEL_TRACES_SAMPLER_ARG=1.0                 # Sampling rate (0.0 to 1.0)
```

### Usage Examples:
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

### Validation:
- [x] Traces visible in tracing backend
- [x] Cross-service tracing works (via context propagation)

---

## 12.5 Prometheus Metrics Enhancement ✅

### Files created/updated:
- [x] `app/core/metrics.py` — Enhanced metrics with system, auth, WebSocket, webhook metrics
- [x] `grafana/dashboards/api-overview.json` — API request metrics dashboard
- [x] `grafana/dashboards/database-redis.json` — Database and cache metrics dashboard
- [x] `grafana/dashboards/business-metrics.json` — Business, jobs, and AI metrics dashboard
- [x] `grafana/README.md` — Dashboard installation guide
- [x] `tests/unit/test_metrics.py` — Unit tests (54 tests)

### Checklist:
- [x] Request metrics:
  - [x] Request count by endpoint (`http_requests_total`)
  - [x] Request latency histogram (`http_request_duration_seconds`)
  - [x] Response status codes
  - [x] Requests in progress (`http_requests_in_progress`)
- [x] Business metrics:
  - [x] Active users (`users_total`)
  - [x] Active subscriptions (`active_subscriptions_total`)
  - [x] API key usage (`api_key_usage_total`)
- [x] System metrics:
  - [x] Process memory (`process_memory_bytes`)
  - [x] CPU time (`process_cpu_seconds_total`)
  - [x] Open file descriptors (`process_open_fds`)
  - [x] Thread count (`process_threads`)
  - [x] App uptime (`app_uptime_seconds`)
  - [x] System info (`system_info`)
- [x] Database metrics:
  - [x] Database pool stats (`db_pool_connections`)
  - [x] Query count/latency (`db_queries_total`, `db_query_duration_seconds`)
  - [x] Database errors (`db_errors_total`)
- [x] Cache metrics:
  - [x] Redis connection stats (`redis_connections`)
  - [x] Cache hits/misses (`cache_hits_total`, `cache_misses_total`)
- [x] Background job metrics:
  - [x] Jobs queued/completed/failed (`background_jobs_total`)
  - [x] Job duration (`background_job_duration_seconds`)
  - [x] Queue size (`background_job_queue_size`)
- [x] Authentication metrics:
  - [x] Auth events (`auth_events_total`)
  - [x] Auth failures (`auth_failures_total`)
  - [x] Token operations (`token_operations_total`)
  - [x] Active sessions (`active_sessions`)
- [x] Rate limiting metrics:
  - [x] Rate limit hits (`rate_limit_hits_total`)
- [x] WebSocket metrics:
  - [x] Connections (`websocket_connections`)
  - [x] Messages (`websocket_messages_total`)
- [x] Webhook metrics:
  - [x] Events processed (`webhook_events_total`)
  - [x] Processing latency (`webhook_processing_duration_seconds`)
- [x] LLM/AI metrics:
  - [x] Requests (`llm_requests_total`)
  - [x] Token usage (`llm_tokens_total`)
  - [x] Latency (`llm_request_duration_seconds`)
- [x] MetricsMiddleware for automatic request tracking
- [x] Grafana dashboard templates

### Features:
- **MetricsMiddleware**: ASGI middleware for automatic HTTP request metrics
- **Path normalization**: Replaces UUIDs and numeric IDs with `{id}` for cleaner metrics
- **System metrics collection**: `update_system_metrics()` for periodic collection
- **Metrics snapshot**: `collect_metrics_snapshot()` for health checks
- **Graceful fallback**: Works without prometheus_client installed (DummyMetric)

### Grafana Dashboards:
1. **API Overview**: Request rate, latency percentiles, error rates, top endpoints
2. **Database & Redis**: Connection pools, query performance, cache hit rates
3. **Business Metrics**: Users, subscriptions, background jobs, AI/LLM usage

### Validation:
- [x] Metrics endpoint returns Prometheus format
- [x] Grafana dashboards work
- [x] 54 unit tests passing

---

## 12.6 Contact Form / Public Endpoints ✅

### Files created:
- [x] `app/api/v1/public/contact.py` — Contact form endpoints
- [x] `app/models/contact_submission.py` — ContactSubmission model
- [x] `migrations/versions/20260111_120000_add_contact_submission_model.py` — Migration
- [x] `tests/unit/test_contact.py` — Unit tests (32 tests)

### Checklist:
- [x] Contact form submission:
  - [x] Required fields: name, email, message
  - [x] Optional fields: subject, phone, company (configurable as required)
  - [x] Custom fields: extra_fields dict for any additional data
  - [x] Source tracking for analytics
  - [x] Configurable rate limit (CONTACT_RATE_LIMIT)
  - [x] Send email notification to admin
  - [x] Database persistence (ContactSubmission model)
  - [x] Redis cache (7 days TTL)
- [x] Confirmation email:
  - [x] Send to sender (configurable via CONTACT_SEND_CONFIRMATION)
  - [x] Include reference number
- [x] Webhook integration:
  - [x] Generic webhook (CONTACT_WEBHOOK_URL)
  - [x] Signature header for verification
  - [x] Compatible with Zapier/Make/n8n
- [x] Spam protection:
  - [x] Honeypot field for spam
  - [x] Timing-based bot detection
- [x] Status endpoint with config info

### Configuration:
- `CONTACT_REQUIRE_SUBJECT` - Make subject required (default: false)
- `CONTACT_REQUIRE_PHONE` - Make phone required (default: false)
- `CONTACT_SEND_CONFIRMATION` - Send confirmation email (default: true)
- `CONTACT_WEBHOOK_URL` - Webhook URL for CRM integrations
- `CONTACT_RATE_LIMIT` - Rate limit string (default: "5/hour")

### Validation:
- [x] Contact form works with modular fields
- [x] Rate limiting prevents spam
- [x] Honeypot catches bots
- [x] Confirmation emails sent
- [x] Webhooks fire on submission

---

## 12.7 Usage-Based Billing ✅

### Files created:
- [x] `app/services/payments/usage.py` — UsageTracker and StripeUsageReporter services
- [x] `app/models/usage_record.py` — UsageRecord model for PostgreSQL persistence
- [x] `app/api/v1/admin/usage.py` — Admin usage analytics endpoints
- [x] `app/api/v1/app/usage.py` — User usage endpoints
- [x] `tests/unit/test_usage.py` — Unit tests (32 tests)

### Checklist:
- [x] Track API usage per user
- [x] Track AI token usage
- [x] Track storage usage
- [x] Usage reports endpoint
- [x] Stripe usage-based billing integration:
  - [x] Report usage to Stripe
  - [x] StripeUsageReporter class
- [x] Usage analytics (trends, growth, daily breakdown)
- [x] UsageTrackingMiddleware for automatic API request tracking

### Features:
- **UsageMetric enum**: api_requests, ai_tokens, ai_requests, storage_bytes, file_uploads, file_downloads, websocket_messages, background_jobs, email_sent
- **Redis-based storage**: Hot storage with `usage:{user_id}:{metric}:{period}` keys
- **In-memory fallback**: Works without Redis
- **Category breakdown**: By endpoint, AI model, file type
- **Trend analysis**: Growth rate, daily averages, peak detection

### Validation:
- [x] Usage tracked correctly
- [x] Stripe reporting configured (StripeUsageReporter)
- [x] 32 tests passing

---

## 12.8 SQLite Fallback for Offline Development ✅

### Files created:
- [x] `app/models/compat.py` — Cross-database compatibility utilities
- [x] `tests/unit/test_sqlite_fallback.py` — Unit tests (33 tests)

### Files updated:
- [x] `app/core/config.py` — SQLite detection and default URL
- [x] `app/core/db.py` — SQLite-compatible engine configuration
- [x] `app/core/cache.py` — In-memory cache fallback

### Checklist:
- [x] Detect SQLite URL (`is_sqlite` computed property)
- [x] Use aiosqlite driver
- [x] Handle SQLite-specific limitations:
  - [x] StaticPool for connection handling
  - [x] check_same_thread=False for aiosqlite
  - [x] JSON instead of JSONB
  - [x] JSON instead of ARRAY
- [x] Graceful fallback when Postgres unavailable
- [x] In-memory cache when Redis unavailable

### Features:
- **SQLite detection**: Automatic via `settings.is_sqlite`
- **InMemoryCache**: Full Redis-compatible API with TTL, hash, set operations
- **Cross-database compatibility**: `JSONColumn()`, `ArrayColumn()`, `JSONEncodedList`, `JSONEncodedDict`
- **Zero-config offline**: Just run `make dev` without Docker

### Validation:
- [x] App runs with SQLite
- [x] Basic operations work
- [x] 33 tests passing

---

## Phase 12 Completion Criteria

- [x] API versioning with v1 and v2 routes
- [x] WebSocket real-time updates work
- [x] Admin dashboard endpoints functional
- [x] Feature flags system working
- [x] OpenTelemetry traces visible
- [x] Prometheus metrics comprehensive
- [x] Contact form with spam protection
- [x] Usage-based billing tracked
- [x] SQLite fallback for offline development

## Current Progress: 8/8 features complete ✅

| Feature | Status | Tests |
|---------|--------|-------|
| 12.1 API Versioning | ✅ Complete | 38 |
| 12.2 WebSocket | ✅ Complete | 23 |
| 12.3 Admin Dashboard | ✅ Complete | 31 |
| 12.4 OpenTelemetry | ✅ Complete | 38 |
| 12.5 Enhanced Metrics | ✅ Complete | 54 |
| 12.6 Contact Form | ✅ Complete | 32 |
| 12.7 Usage-Based Billing | ✅ Complete | 32 |
| 12.8 SQLite Fallback | ✅ Complete | 33 |

**Total Phase 12 Tests:** 281

---

## Files Created in Phase 12

| File | Purpose | Status |
|------|---------|--------|
| `app/api/v1/app/ws.py` | WebSocket endpoints | ✅ |
| `app/services/websocket/manager.py` | WS connection manager | ✅ |
| `app/services/websocket/events.py` | Event types | ✅ |
| `app/services/websocket/__init__.py` | Package exports | ✅ |
| `app/api/v1/admin/dashboard.py` | Dashboard stats | ✅ |
| `app/api/v1/admin/feature_flags.py` | Feature flags CRUD | ✅ |
| `app/api/v1/admin/impersonate.py` | User impersonation | ✅ |
| `app/models/feature_flag.py` | Feature flag model | ✅ |
| `app/models/audit_log.py` | Audit log model | ✅ |
| `tests/unit/test_websocket.py` | WebSocket tests (23) | ✅ |
| `tests/unit/test_admin_dashboard.py` | Admin dashboard tests (31) | ✅ |
| `app/api/v1/public/contact.py` | Contact form | ✅ |
| `app/models/contact_submission.py` | Contact submission model | ✅ |
| `tests/unit/test_contact.py` | Contact form tests (32) | ✅ |
| `app/core/versioning.py` | Version utilities | ✅ |
| `app/api/v2/__init__.py` | Version 2 package | ✅ |
| `app/api/v2/router.py` | Version 2 router | ✅ |
| `app/api/v2/public/health.py` | v2 health endpoints | ✅ |
| `app/api/v2/app/users.py` | v2 user endpoints | ✅ |
| `tests/unit/test_versioning.py` | Versioning tests (38) | ✅ |
| `app/core/tracing.py` | OpenTelemetry setup | ✅ |
| `tests/unit/test_tracing.py` | Tracing tests (38) | ✅ |
| `app/core/metrics.py` | Enhanced metrics | ✅ |
| `tests/unit/test_metrics.py` | Metrics tests (54) | ✅ |
| `grafana/dashboards/*.json` | Grafana dashboards | ✅ |
| `grafana/README.md` | Dashboard guide | ✅ |
| `app/services/payments/usage.py` | Usage tracking | ✅ |
| `app/models/usage_record.py` | Usage record model | ✅ |
| `app/api/v1/admin/usage.py` | Admin usage endpoints | ✅ |
| `app/api/v1/app/usage.py` | User usage endpoints | ✅ |
| `tests/unit/test_usage.py` | Usage tests (32) | ✅ |
| `app/models/compat.py` | SQLite compatibility | ✅ |
| `tests/unit/test_sqlite_fallback.py` | SQLite fallback tests (33) | ✅ |
