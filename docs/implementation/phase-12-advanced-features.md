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

## 12.3 Admin Dashboard Endpoints

### Files to create:
- [ ] `app/api/v1/admin/dashboard.py` — Dashboard stats
- [ ] `app/api/v1/admin/feature_flags.py` — Feature flags
- [ ] `app/api/v1/admin/impersonate.py` — User impersonation

### Checklist:
- [ ] User management:
  - [ ] List all users with pagination/search
  - [ ] User details view
  - [ ] Update user role/status
  - [ ] Impersonate user (for debugging)
- [ ] Feature flags:
  - [ ] Create/update/delete flags
  - [ ] Enable per user/percentage
  - [ ] Check flag status
- [ ] System metrics:
  - [ ] Active users count
  - [ ] Request counts
  - [ ] Error rates
  - [ ] Background job stats
- [ ] Webhook logs:
  - [ ] View webhook history
  - [ ] Retry failed webhooks
- [ ] Audit log:
  - [ ] Track admin actions
  - [ ] Who did what when

### Files to create:
- [ ] `app/models/feature_flag.py`
- [ ] `app/models/audit_log.py`

### Validation:
- [ ] Admin endpoints secured
- [ ] Feature flags work
- [ ] Impersonation works safely

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

## 12.6 Contact Form / Public Endpoints

### Files to create:
- [ ] `app/api/v1/public/contact.py` — Contact form

### Checklist:
- [ ] Contact form submission:
  - [ ] Validate input
  - [ ] Rate limit (prevent spam)
  - [ ] Send email notification
  - [ ] Store in database (optional)
- [ ] Captcha integration (optional):
  - [ ] reCAPTCHA v3
  - [ ] hCaptcha
- [ ] Honeypot field for spam

### Validation:
- [ ] Contact form works
- [ ] Rate limiting prevents spam

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

| File | Purpose |
|------|---------|
| `app/api/v2/router.py` | Version 2 API |
| `app/core/versioning.py` | Version utilities |
| `app/api/v1/app/ws.py` | WebSocket endpoints |
| `app/services/websocket/manager.py` | WS connection manager |
| `app/api/v1/admin/dashboard.py` | Dashboard stats |
| `app/api/v1/admin/feature_flags.py` | Feature flags |
| `app/models/feature_flag.py` | Feature flag model |
| `app/models/audit_log.py` | Audit log model |
| `app/core/tracing.py` | OpenTelemetry setup |
| `app/api/v1/public/contact.py` | Contact form |
| `app/services/payments/usage.py` | Usage tracking |
