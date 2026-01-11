# OmniStack Backend Boilerplate — Product Requirements Document

**Version:** 1.0  
**Last Updated:** January 2026  
**Author:** Logixtecs Solutions LLC

---

## Executive Summary

OmniStack is a production-ready FastAPI backend boilerplate designed for solo developers and small teams who need "Senior-Level" architecture from Day 1. The goal is to eliminate the 2-4 weeks of setup overhead that comes with every new SaaS project, allowing developers to ship their first feature within hours, not days.

**Core Philosophy:** "Zero to API in 60 seconds, Zero to Production in 60 minutes."

---

## Problem Statement

### The Current Pain Points

Every time a developer starts a new SaaS backend, they face the same tedious setup:

1. **Auth Integration Hell** — Choosing between Clerk, Supabase, Auth0, then figuring out JWT verification, JWKS endpoints, and user syncing.

2. **Database Boilerplate** — Setting up async connections, migrations, and CRUD patterns that work across local Docker and serverless Postgres.

3. **Infrastructure Decisions** — Redis vs. in-memory cache, S3 vs. R2, SendGrid vs. Resend — each requiring different SDKs and patterns.

4. **The "Glue Code" Problem** — Rate limiting, CORS, error handling, logging, health checks — none are complex individually, but together they consume 40+ hours.

5. **Environment Confusion** — Managing local, staging, and production configs without leaking secrets or breaking deployments.

6. **Missing Production Essentials** — Error tracking, background jobs, webhooks, payments — always added as afterthoughts.

### The Cost

- **2-4 weeks** lost on every new project before writing actual business logic
- **$5,000-15,000** in developer time (at $50-75/hr) per project
- **Technical debt** from rushed implementations that "just work for now"

---

## Solution: OmniStack Backend Boilerplate

A **plug-and-play FastAPI template** where every infrastructure decision is pre-made but swappable. Change your auth provider, database host, or AI model with a single environment variable — no code rewrites.

### Target Users

| User Type | Need | How OmniStack Helps |
|-----------|------|---------------------|
| Solo Founders | Ship MVP fast | Pre-built auth, payments, email — focus on your differentiator |
| Agency Developers | Consistent project starts | Same architecture across all client projects |
| Indie Hackers | Production-ready from Day 1 | No more "I'll add proper error handling later" |
| Small Teams (2-5) | Shared conventions | Everyone knows where things live |

---

## Product Goals & Success Metrics

### Primary Goals

1. **Time to First Protected Endpoint:** < 10 minutes from `git clone`
2. **Time to Production Deploy:** < 60 minutes (Railway/Render one-click)
3. **Provider Switch Time:** < 5 minutes to change auth/db/cache provider
4. **Zero Lock-in:** No proprietary abstractions — just clean Python patterns

### Success Metrics

| Metric | Target | How We Measure |
|--------|--------|----------------|
| Setup Time | < 60 seconds | `make dev` → API responding |
| First Deploy | < 60 minutes | Clone → Live URL |
| Provider Swap | 1 file + .env | No business logic changes |
| Test Coverage | > 80% | Pytest report |
| Documentation | Self-documenting | OpenAPI + inline comments |

---

## Core Features

### Tier 1: "Must Ship" (v1.0)

These features are non-negotiable for the initial release.

#### 1. Universal Authentication

**Problem:** Every auth provider (Clerk, Supabase, Auth0) has different JWT formats, verification methods, and user data structures.

**Solution:** A single `verify_token()` dependency that works with any provider.

| Provider | Verification Method | Config Required |
|----------|---------------------|-----------------|
| Supabase (New) | JWKS/RS256 | `SUPABASE_PROJECT_URL` |
| Supabase (Legacy) | HS256 Secret | `SUPABASE_JWT_SECRET` |
| Clerk | JWKS/RS256 | `CLERK_ISSUER_URL` |
| Custom OAuth2 | JWKS/RS256 | `OAUTH_JWKS_URL` |

**User Stories:**
- As a developer, I can switch from Supabase to Clerk by changing 2 env vars
- As a developer, I can access `current_user` in any protected route
- As a developer, I can add role-based access with a single decorator

#### 2. Async Database Layer

**Problem:** Configuring async Postgres with proper connection pooling, migrations, and ORM patterns.

**Solution:** SQLModel + Alembic with async support, pre-configured for both local Docker and serverless (Neon, Supabase).

**Capabilities:**
- Auto-generated migrations from model changes
- Connection pooling optimized for serverless (NullPool option)
- Generic CRUD base class for instant repositories
- Transaction management helpers

**User Stories:**
- As a developer, I can define a model and have migrations auto-generated
- As a developer, I can switch from local Postgres to Neon with one env var
- As a developer, I can create full CRUD endpoints in < 20 lines of code

#### 3. Smart Rate Limiting

**Problem:** Protecting expensive endpoints (AI, payments) without blocking legitimate users.

**Solution:** Redis-backed rate limiting with route-specific configs.

| Route Type | Default Limit | Storage |
|------------|---------------|---------|
| Public | 60/min | Redis |
| Protected | 120/min | Redis |
| AI Endpoints | 10/min | Redis |
| Webhooks | 1000/min | In-memory |

**User Stories:**
- As a developer, I can set per-route rate limits with a decorator
- As a developer, I can switch from local Redis to Upstash with one env var
- As a developer, I can see rate limit headers in API responses

#### 4. Background Jobs

**Problem:** Long-running tasks (email, AI processing, reports) blocking API responses.

**Solution:** ARQ (async Redis queue) for lightweight task processing.

**Why ARQ over Celery:**
- Pure async Python (no worker processes needed in dev)
- Redis-only (no RabbitMQ complexity)
- 10x simpler API
- Perfect for serverless environments

**User Stories:**
- As a developer, I can offload email sending to background with `@background_task`
- As a developer, I can schedule recurring tasks (daily reports) with cron syntax
- As a developer, I can monitor job status via admin endpoints

#### 5. Multi-Provider AI Gateway

**Problem:** Different AI providers have different SDKs, rate limits, and pricing. Switching or load-balancing is painful.

**Solution:** Unified `LLMService` with automatic model routing.

**Supported Providers:**
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Haiku)
- Google (Gemini Pro)
- Perplexity (for search-augmented responses)

**Smart Routing:**
```
Simple tasks (classification, extraction) → GPT-4o-mini ($0.15/1M tokens)
Complex tasks (reasoning, coding) → Claude 3.5 Sonnet ($3/1M tokens)
Search tasks (current events) → Perplexity
```

**User Stories:**
- As a developer, I can call `llm.complete(prompt, complexity="simple")` and get auto-routed
- As a developer, I can add fallback providers if primary is rate-limited
- As a developer, I can track AI costs per user in the dashboard

#### 6. Email Service Abstraction

**Problem:** Email providers (SendGrid, Resend, Postmark) all have different APIs.

**Solution:** Unified `EmailService` with template support.

**User Stories:**
- As a developer, I can send transactional emails with `email.send(to, template, data)`
- As a developer, I can switch from SendGrid to Resend with one env var
- As a developer, I can preview email templates locally without sending

#### 7. File Storage Abstraction

**Problem:** S3-compatible storage (AWS S3, Cloudflare R2, MinIO) needs consistent upload/download patterns.

**Solution:** Unified `StorageService` with presigned URL support.

**User Stories:**
- As a developer, I can generate presigned upload URLs for client-side uploads
- As a developer, I can switch from S3 to R2 with one env var
- As a developer, I can set per-file type size limits

#### 8. Webhook Infrastructure

**Problem:** Receiving webhooks from Stripe, Clerk, etc. requires signature verification and idempotency.

**Solution:** Pre-built webhook handlers with automatic verification.

**Supported Webhooks:**
- Stripe (payment events)
- Clerk (user events)
- Supabase (auth events)
- Generic (custom HMAC verification)

**User Stories:**
- As a developer, I can add a Stripe webhook handler in 5 lines
- As a developer, I can trust that duplicate webhooks are automatically ignored
- As a developer, I can see webhook logs in the admin dashboard

#### 9. Developer Experience (DX) Commands

**Problem:** Remembering Docker commands, migration syntax, and test runners.

**Solution:** Makefile with all common operations.

| Command | Action |
|---------|--------|
| `make dev` | Start API with hot reload |
| `make up` | Start Docker services (DB, Redis) |
| `make down` | Stop all services |
| `make migrate` | Generate + apply migrations |
| `make test` | Run Pytest suite |
| `make lint` | Run Ruff + Black |
| `make seed` | Populate DB with test data |
| `make shell` | Open Python REPL with app context |

#### 10. Production Essentials

**Health Checks:**
- `/health` — Basic liveness probe
- `/health/ready` — Full readiness (DB, Redis, external services)

**Error Tracking:**
- Sentry integration with automatic context capture
- Custom error codes for client-side handling

**Logging:**
- JSON-structured logs for Datadog/Railway/Render
- Request ID tracking across async operations
- Automatic PII redaction

---

### Tier 2: "Should Have" (v1.1)

Features that significantly improve the developer experience but aren't blockers.

#### 11. Stripe Integration

Pre-built patterns for:
- Checkout sessions
- Subscription management
- Usage-based billing
- Invoice webhooks

#### 12. Admin Dashboard Endpoints

- User management (list, search, impersonate)
- Feature flags
- System metrics
- Background job monitoring

#### 13. API Versioning Strategy

- `/api/v1/...` and `/api/v2/...` routing
- Deprecation headers
- Version-specific middleware

#### 14. WebSocket Support

- Real-time notifications
- Live updates (dashboards, feeds)
- Connection management

---

### Tier 3: "Nice to Have" (v1.2+)

#### 15. Multi-tenancy Patterns

- Organization/workspace isolation
- Tenant-specific rate limits
- Data partitioning strategies

#### 16. GraphQL Layer (Optional)

- Strawberry GraphQL integration
- Automatic schema from SQLModel
- Subscription support

#### 17. CLI Tool

- `omni new project-name` — Scaffold new project
- `omni add stripe` — Add Stripe integration
- `omni deploy railway` — One-command deploy

---

## Non-Functional Requirements

### Performance

| Metric | Target |
|--------|--------|
| Cold Start | < 2 seconds |
| P50 Latency | < 50ms (non-AI routes) |
| P99 Latency | < 200ms (non-AI routes) |
| Concurrent Connections | 1000+ |

### Security

- OWASP Top 10 compliance
- Automatic SQL injection prevention (SQLModel)
- XSS protection headers
- CSRF protection for non-API routes
- Secret scanning in CI

### Reliability

- Graceful degradation (Redis down → in-memory fallback)
- Circuit breakers for external services
- Automatic retry with exponential backoff

### Observability

- Distributed tracing (OpenTelemetry compatible)
- Prometheus metrics endpoint
- Custom business metrics hooks

---

## Deployment Targets

### Primary (One-Click)

| Platform | Config File | Est. Cost |
|----------|-------------|-----------|
| Railway | `railway.toml` | $5-20/mo |
| Render | `render.yaml` | $7-25/mo |
| Fly.io | `fly.toml` | $5-20/mo |

### Secondary (Requires Setup)

| Platform | Config File | Est. Cost |
|----------|-------------|-----------|
| AWS (ECS/Fargate) | `docker-compose.yml` + Terraform | $20-100/mo |
| GCP (Cloud Run) | `cloudbuild.yaml` | $10-50/mo |
| DigitalOcean (App Platform) | `app.yaml` | $5-25/mo |

### Local Development

- Docker Compose (Postgres + Redis)
- SQLite fallback for offline development
- In-memory Redis fallback

---

## Project Milestones

### Phase 1: Foundation (Week 1-2)

- [ ] Project structure and folder layout
- [ ] Configuration system (`config.py`)
- [ ] Database connection and base models
- [ ] Authentication (Supabase + Clerk)
- [ ] Basic rate limiting
- [ ] Health check endpoints
- [ ] Makefile commands
- [ ] Docker Compose setup

### Phase 2: Core Services (Week 3-4)

- [ ] Generic CRUD base class
- [ ] Background job infrastructure (ARQ)
- [ ] Email service abstraction
- [ ] Storage service abstraction
- [ ] AI gateway (OpenAI + Anthropic)
- [ ] Webhook handlers (Stripe, Clerk)

### Phase 3: Production Ready (Week 5-6)

- [ ] Sentry integration
- [ ] Structured logging
- [ ] CI/CD pipelines (GitHub Actions)
- [ ] Deployment configs (Railway, Render, Fly)
- [ ] Documentation site
- [ ] Test suite (80%+ coverage)

### Phase 4: Polish (Week 7-8)

- [ ] Admin endpoints
- [ ] Seed data commands
- [ ] Example app (Todo SaaS)
- [ ] Video tutorials
- [ ] Community templates

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FastAPI breaking changes | High | Pin versions, test against pre-releases |
| Provider API changes | Medium | Adapter pattern isolates changes |
| Scope creep | High | Strict tier system, say no to "cool but unnecessary" |
| Documentation debt | Medium | Doc-first development, auto-generate from code |

---

## Appendix: Competitor Analysis

| Feature | OmniStack | FastAPI Template | Django Cookiecutter |
|---------|-----------|------------------|---------------------|
| Auth Provider Switching | ✅ | ❌ | ❌ |
| Async-First | ✅ | ✅ | ❌ |
| AI Gateway | ✅ | ❌ | ❌ |
| Background Jobs | ✅ (ARQ) | ❌ | ✅ (Celery) |
| One-Command Setup | ✅ | ⚠️ | ✅ |
| Serverless-Ready | ✅ | ⚠️ | ❌ |
| TypeScript Frontend | Planned | ❌ | ❌ |

---

## Next Steps

1. **Review this PRD** — Identify any missing requirements
2. **Create Technical PRD** — Detailed implementation specs
3. **Set up repository** — Initialize with folder structure
4. **Begin Phase 1** — Configuration system first

---

*This document is the single source of truth for OmniStack Backend Boilerplate requirements.*
