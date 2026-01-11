# Phase 12: Advanced Features (v1.1)

**Duration:** Enhancement phase
**Goal:** Add Tier 2 features - WebSocket, API versioning, admin dashboard, observability

**Prerequisites:** Phase 1-11 completed (Core v1.0)

**Note:** This phase is optional for v1.0 but recommended for production SaaS

---

## 12.1 API Versioning Strategy

### Files to create/update:
- [ ] `app/api/v2/__init__.py` — Version 2 routes
- [ ] `app/api/v2/router.py`
- [ ] `app/core/versioning.py` — Version utilities

### Checklist:
- [ ] `/api/v1/...` and `/api/v2/...` routing structure
- [ ] Version-specific routers
- [ ] Deprecation headers for old endpoints
- [ ] Version detection from header (optional)
- [ ] Version-specific middleware
- [ ] Sunset header for deprecated endpoints
- [ ] Documentation per version

### Validation:
- [ ] Both v1 and v2 routes work
- [ ] Deprecation warnings visible

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

## 12.4 OpenTelemetry / Distributed Tracing

### Files to create:
- [ ] `app/core/tracing.py` — OpenTelemetry setup

### Checklist:
- [ ] OpenTelemetry SDK integration
- [ ] Trace context propagation
- [ ] Span creation for:
  - [ ] HTTP requests
  - [ ] Database queries
  - [ ] External API calls
  - [ ] Background jobs
- [ ] Export to:
  - [ ] Jaeger (self-hosted)
  - [ ] Datadog
  - [ ] Honeycomb
- [ ] Correlation with logs (trace ID in logs)
- [ ] Custom attributes on spans

### Validation:
- [ ] Traces visible in tracing backend
- [ ] Cross-service tracing works

---

## 12.5 Prometheus Metrics Enhancement

### Files to update:
- [ ] `app/core/metrics.py` — Enhanced metrics

### Checklist:
- [ ] Request metrics:
  - [ ] Request count by endpoint
  - [ ] Request latency histogram
  - [ ] Response status codes
- [ ] Business metrics:
  - [ ] Active users
  - [ ] Signups per day
  - [ ] API calls per user
- [ ] System metrics:
  - [ ] Database pool stats
  - [ ] Redis connection stats
  - [ ] Memory usage
- [ ] Background job metrics:
  - [ ] Jobs queued/completed/failed
  - [ ] Job duration
- [ ] Custom metric hooks for business logic
- [ ] Grafana dashboard templates

### Validation:
- [ ] Metrics endpoint returns Prometheus format
- [ ] Grafana dashboards work

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

## 12.7 Usage-Based Billing

### Files to create:
- [ ] `app/services/payments/usage.py` — Usage tracking

### Checklist:
- [ ] Track API usage per user
- [ ] Track AI token usage
- [ ] Track storage usage
- [ ] Usage reports endpoint
- [ ] Stripe usage-based billing integration:
  - [ ] Report usage to Stripe
  - [ ] Usage-based price IDs
- [ ] Usage alerts (approaching limit)

### Validation:
- [ ] Usage tracked correctly
- [ ] Stripe receives usage reports

---

## 12.8 SQLite Fallback for Offline Development

### Files to update:
- [ ] `app/core/db.py` — SQLite support

### Checklist:
- [ ] Detect SQLite URL
- [ ] Use aiosqlite driver
- [ ] Handle SQLite-specific limitations
- [ ] Graceful fallback when Postgres unavailable

### Validation:
- [ ] App runs with SQLite
- [ ] Basic operations work

---

## Phase 12 Completion Criteria

- [ ] API versioning with v1 and v2 routes
- [ ] WebSocket real-time updates work
- [ ] Admin dashboard endpoints functional
- [ ] Feature flags system working
- [ ] OpenTelemetry traces visible
- [ ] Prometheus metrics comprehensive
- [ ] Contact form with spam protection
- [ ] Usage-based billing tracked

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
| `app/api/v2/router.py` | Version 2 API | 🔴 |
| `app/core/versioning.py` | Version utilities | 🔴 |
| `app/core/tracing.py` | OpenTelemetry setup | 🔴 |
| `app/services/payments/usage.py` | Usage tracking | 🔴 |
