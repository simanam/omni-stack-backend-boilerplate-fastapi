# OmniStack Backend Boilerplate

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://simanam.github.io/omni-stack-backend-boilerplate-fastapi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

Production-ready FastAPI backend boilerplate for SaaS applications.

**Goal:** "Zero to API in 60 seconds, Zero to Production in 60 minutes"

**[View Full Documentation](https://simanam.github.io/omni-stack-backend-boilerplate-fastapi/)**

---

## Quick Start

```bash
# 1. Create virtual environment
make venv

# 2. Activate it
source .venv/bin/activate

# 3. Install dependencies
make install

# 4. Copy environment file
cp .env.example .env

# 5. Start Postgres and Redis
make up

# 6. Run API with hot reload
make dev
```

**That's it!** API available at `http://localhost:8000`

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/api/v1/public/health | Health check |

---

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| ORM | SQLModel (Pydantic + SQLAlchemy) | 0.0.22+ |
| Database | PostgreSQL | 16+ |
| Cache | Redis | 7+ |
| Migrations | Alembic | 1.13+ |
| Background Jobs | ARQ | 0.26+ |
| Testing | Pytest | 8.3+ |
| Linting | Ruff | 0.7+ |

---

## Features

### Core
- JWT Authentication (Supabase, Clerk, Custom OAuth)
- Generic CRUD operations with pagination
- Soft delete support
- Rate limiting (Redis-backed)
- Request/Response logging
- Security headers (CORS, CSP, HSTS)
- WebSocket support for real-time features

### External Services (Pluggable)
- **AI Gateway**: OpenAI, Anthropic, Google Gemini
- **Email**: Resend, SendGrid
- **Storage**: AWS S3, Cloudflare R2, Cloudinary
- **Payments**: Stripe (web), Apple IAP, Google Play

### Admin Features
- Dashboard with system metrics
- Feature flags (boolean, percentage, user-based, plan-based)
- User impersonation for support
- Audit logging

### Public Endpoints
- Contact form with modular fields
- CRM webhook integration (Zapier/Make/n8n compatible)
- Confirmation emails

### Observability
- OpenTelemetry distributed tracing (OTLP, Zipkin)
- Prometheus metrics
- Sentry error tracking
- Structured JSON logging with trace correlation

---

## Documentation

**[Full Documentation Site](https://simanam.github.io/omni-stack-backend-boilerplate-fastapi/)** | [Source Files](./documentation/)

Comprehensive documentation available online and in the [`documentation/`](./documentation/) folder:

| Document | Description | Best For |
|----------|-------------|----------|
| [Getting Started](./documentation/GETTING-STARTED.md) | Setup, environment variables, troubleshooting | New developers |
| [API Reference](./documentation/API-REFERENCE.md) | All endpoints, request/response formats, error codes | Frontend developers |
| [Architecture](./documentation/ARCHITECTURE.md) | System design, naming conventions, patterns | Backend developers |
| [Modular Guide](./documentation/MODULAR-GUIDE.md) | Pick & choose components, minimal setups | Customizing the boilerplate |
| [Frontend Integration](./documentation/FRONTEND-INTEGRATION.md) | TypeScript types, React examples, API client setup | Frontend/Mobile developers |
| [Contributing](./documentation/CONTRIBUTING.md) | Code style, testing, PR process | Contributors |

### Quick Links

**For Frontend Developers:**
- [API Endpoints](./documentation/API-REFERENCE.md#endpoints)
- [Response Formats](./documentation/API-REFERENCE.md#response-formats)
- [Error Handling](./documentation/API-REFERENCE.md#error-responses)
- [TypeScript Types](./documentation/FRONTEND-INTEGRATION.md#typescript-types)
- [Authentication Flow](./documentation/FRONTEND-INTEGRATION.md#authentication)

**For Backend Developers:**
- [Project Structure](./documentation/ARCHITECTURE.md#project-structure)
- [Naming Conventions](./documentation/ARCHITECTURE.md#naming-conventions)
- [Adding New Features](./documentation/ARCHITECTURE.md#adding-new-features)
- [Database Patterns](./documentation/ARCHITECTURE.md#database-patterns)

**For DevOps:**
- [Environment Variables](./documentation/GETTING-STARTED.md#environment-variables)
- [Docker Deployment](./documentation/GETTING-STARTED.md#using-docker)
- [CI/CD Pipelines](./documentation/ARCHITECTURE.md#cicd-pipelines)
- [Deployment Guide](./docs/DEPLOYMENT.md)

---

## API Structure

```
/api/v1/
├── public/          # No authentication required
│   ├── health       # Health checks
│   ├── contact      # Contact form submissions
│   ├── webhooks/    # Stripe, Supabase, Clerk webhooks
│   └── metrics      # Prometheus metrics
│
├── app/             # Authentication required
│   ├── users/       # User profile
│   ├── projects/    # Project CRUD
│   ├── files/       # File upload/download
│   ├── ai/          # AI completions
│   ├── billing/     # Subscriptions
│   └── ws           # WebSocket connections
│
└── admin/           # Admin role required
    ├── users/       # User management
    ├── jobs/        # Background job monitoring
    ├── dashboard/   # System metrics & stats
    ├── feature-flags/ # Feature flag management
    └── impersonate/ # User impersonation
```

---

## Project Structure

```
backend-boilerplate-fastapi/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/                 # HTTP endpoints
│   │   ├── deps.py          # Dependencies (auth, db)
│   │   └── v1/              # API version 1
│   ├── core/                # Config, DB, security, middleware
│   ├── models/              # SQLModel database models
│   ├── schemas/             # Pydantic schemas
│   ├── business/            # Business logic services
│   ├── services/            # External service adapters
│   │   ├── ai/              # OpenAI, Anthropic, Gemini
│   │   ├── email/           # Resend, SendGrid
│   │   ├── storage/         # S3, R2, Cloudinary
│   │   ├── payments/        # Stripe, Apple IAP, Google IAP
│   │   └── websocket/       # Real-time WebSocket manager
│   └── jobs/                # Background tasks (ARQ)
├── migrations/              # Alembic migrations
├── tests/                   # Test suite
├── docker/                  # Docker configuration
├── documentation/           # Comprehensive docs
├── .github/workflows/       # CI/CD pipelines
└── docs/                    # Deployment & backup guides
```

---

## Make Commands

| Command | Description |
|---------|-------------|
| `make venv` | Create Python virtual environment |
| `make install` | Install all dependencies |
| `make dev` | Run API with hot reload |
| `make up` | Start Docker services (DB + Redis) |
| `make down` | Stop Docker services |
| `make test` | Run test suite |
| `make lint` | Run linter (Ruff) |
| `make worker` | Start background worker |
| `make migrate msg="description"` | Generate and run migration |

---

## Environment Variables

Minimal `.env` for development:

```bash
SECRET_KEY="your-secret-key-at-least-32-characters-long"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/omnistack"
REDIS_URL="redis://localhost:6379/0"
```

See [`.env.example`](./.env.example) for all available variables or [Environment Variables documentation](./documentation/GETTING-STARTED.md#environment-variables).

---

## Modular Architecture

This boilerplate is designed like Lego blocks. Pick only what you need:

| Component | Keep For | Remove If |
|-----------|----------|-----------|
| AI Gateway | AI-powered features | No AI needed |
| Email Service | Transactional emails | Using auth provider email |
| Storage Service | File uploads | Using Supabase Storage |
| Stripe | Web subscriptions | No web payments |
| Apple/Google IAP | Mobile apps | Web-only |
| Background Jobs | Async processing | No async tasks |

See the [Modular Guide](./documentation/MODULAR-GUIDE.md) for detailed removal instructions.

---

## Testing

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific tests
pytest tests/unit/ -v
pytest tests/integration/ -v
```

---

## Deployment

Pre-configured for multiple platforms:

| Platform | Config File |
|----------|-------------|
| Railway | `railway.toml` |
| Render | `render.yaml` |
| Fly.io | `fly.toml` |
| Docker | `docker/Dockerfile` |

See [Deployment Guide](./docs/DEPLOYMENT.md) for detailed instructions.

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](./documentation/CONTRIBUTING.md) for:
- Code style guidelines
- Testing requirements
- Pull request process

---

## License

MIT

---

## Support

- [Full Documentation](https://simanam.github.io/omni-stack-backend-boilerplate-fastapi/)
- [GitHub Issues](https://github.com/simanam/omni-stack-backend-boilerplate-fastapi/issues)
- [GitHub Discussions](https://github.com/simanam/omni-stack-backend-boilerplate-fastapi/discussions)
