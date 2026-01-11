# OmniStack Backend Documentation

Welcome to the OmniStack Backend documentation! This is a production-ready FastAPI backend boilerplate for SaaS applications.

---

## Quick Links

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } __Getting Started__

    ---

    Set up your development environment in 60 seconds

    [:octicons-arrow-right-24: Quick Start](GETTING-STARTED.md)

-   :material-api:{ .lg .middle } __API Reference__

    ---

    Complete endpoint documentation with request/response examples

    [:octicons-arrow-right-24: API Docs](API-REFERENCE.md)

-   :material-sitemap:{ .lg .middle } __Architecture__

    ---

    System design, patterns, and naming conventions

    [:octicons-arrow-right-24: Architecture](ARCHITECTURE.md)

-   :material-puzzle:{ .lg .middle } __Modular Guide__

    ---

    Pick and choose only the components you need

    [:octicons-arrow-right-24: Customize](MODULAR-GUIDE.md)

-   :material-code-tags:{ .lg .middle } __Frontend Integration__

    ---

    TypeScript types, React, Next.js, iOS, and Android examples

    [:octicons-arrow-right-24: Integration](FRONTEND-INTEGRATION.md)

-   :material-github:{ .lg .middle } __Contributing__

    ---

    Code style, testing requirements, and PR process

    [:octicons-arrow-right-24: Contribute](CONTRIBUTING.md)

</div>

---

## Features

### Core

- **JWT Authentication** - Supabase, Clerk, or custom OAuth
- **Generic CRUD** - Reusable patterns with pagination
- **Soft Delete** - Non-destructive data removal
- **Rate Limiting** - Redis-backed sliding window
- **Security Headers** - CORS, CSP, HSTS

### External Services (Pluggable)

| Service | Providers |
|---------|-----------|
| **AI Gateway** | OpenAI, Anthropic, Google Gemini |
| **Email** | Resend, SendGrid |
| **Storage** | AWS S3, Cloudflare R2, Cloudinary |
| **Payments** | Stripe, Apple IAP, Google Play |

### Observability

- Prometheus metrics
- Sentry error tracking
- Structured JSON logging

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.12+ |
| Framework | FastAPI |
| ORM | SQLModel (Pydantic + SQLAlchemy) |
| Database | PostgreSQL 16+ |
| Cache | Redis 7+ |
| Background Jobs | ARQ |
| Testing | Pytest |
| Linting | Ruff |

---

## Philosophy

> **"Zero to API in 60 seconds, Zero to Production in 60 minutes"**

This boilerplate follows:

- **12-Factor App** - All config via environment variables
- **Adapter Pattern** - Swap providers without changing business logic
- **Clean Architecture** - Business logic separated from HTTP layer
- **Async-First** - Non-blocking I/O everywhere

---

## Support

- [GitHub Issues](https://github.com/simanam/omni-stack-backend-boilerplate-fastapi/issues)
- [GitHub Discussions](https://github.com/simanam/omni-stack-backend-boilerplate-fastapi/discussions)

---

*v1.0 - Production Ready*
