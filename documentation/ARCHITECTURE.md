# Architecture Documentation

Complete guide to the system architecture, design patterns, and code conventions.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Project Structure](#project-structure)
3. [Naming Conventions](#naming-conventions)
4. [Request Lifecycle](#request-lifecycle)
5. [Layer Architecture](#layer-architecture)
6. [Database Patterns](#database-patterns)
7. [Authentication Flow](#authentication-flow)
8. [Error Handling](#error-handling)
9. [Service Adapters](#service-adapters)
10. [Observability](#observability)
11. [Adding New Features](#adding-new-features)

---

## Design Principles

### 1. 12-Factor App Compliance
All configuration via environment variables. No hardcoded secrets or config.

### 2. Adapter Pattern
External services (AI, email, storage) are plugins with abstract interfaces. Swap providers without changing business logic.

### 3. Clean Architecture
Business logic has zero knowledge of HTTP or frameworks. Pure Python functions that can be tested in isolation.

### 4. Async-First
All I/O operations are non-blocking. Use `async`/`await` everywhere.

### 5. Fail-Fast
Invalid configuration fails at startup, not runtime. Better to fail early than produce silent errors.

### 6. Convention Over Configuration
Consistent patterns reduce cognitive load. Follow the established conventions.

---

## Project Structure

```
app/
├── main.py                    # FastAPI application factory
├── __init__.py
│
├── api/                       # HTTP Layer (Controllers)
│   ├── __init__.py
│   ├── deps.py                # Dependency injection
│   └── v1/
│       ├── __init__.py
│       ├── router.py          # Route aggregation
│       ├── public/            # No auth required
│       │   ├── health.py      # Health checks
│       │   ├── webhooks.py    # External webhooks
│       │   └── metrics.py     # Prometheus metrics
│       ├── app/               # Auth required
│       │   ├── users.py       # User endpoints
│       │   ├── projects.py    # Project CRUD
│       │   ├── files.py       # File management
│       │   ├── ai.py          # AI completions
│       │   └── billing.py     # Subscriptions
│       └── admin/             # Admin role required
│           ├── users.py       # User management
│           └── jobs.py        # Job monitoring
│
├── core/                      # Core Infrastructure
│   ├── __init__.py
│   ├── config.py              # Pydantic Settings
│   ├── db.py                  # Database engine & session
│   ├── cache.py               # Redis client
│   ├── security.py            # JWT verification
│   ├── exceptions.py          # Custom exceptions
│   ├── middleware.py          # HTTP middleware
│   ├── sentry.py              # Error tracking
│   ├── metrics.py             # Prometheus metrics
│   ├── tracing.py             # OpenTelemetry tracing
│   └── logging.py             # Structured logging
│
├── models/                    # Database Models (SQLModel)
│   ├── __init__.py
│   ├── base.py                # BaseModel, SoftDeleteMixin
│   ├── user.py                # User model + schemas
│   ├── project.py             # Project model
│   ├── file.py                # File model
│   └── webhook_event.py       # Webhook tracking
│
├── schemas/                   # Request/Response Schemas
│   ├── __init__.py
│   ├── common.py              # Shared schemas
│   ├── user.py                # User schemas (re-exports)
│   ├── project.py             # Project schemas
│   ├── file.py                # File schemas
│   └── ai.py                  # AI schemas
│
├── business/                  # Business Logic Layer
│   ├── __init__.py
│   ├── crud_base.py           # Generic CRUD operations
│   ├── user_service.py        # User business logic
│   ├── project_service.py     # Project business logic
│   ├── billing_service.py     # Billing business logic
│   └── iap_service.py         # Mobile IAP logic
│
├── services/                  # External Service Adapters
│   ├── __init__.py
│   ├── ai/                    # AI providers
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract interface
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── gemini_provider.py
│   │   ├── router.py          # Smart routing
│   │   └── factory.py         # Provider factory
│   ├── email/                 # Email providers
│   │   ├── base.py
│   │   ├── resend_provider.py
│   │   ├── sendgrid_provider.py
│   │   ├── console_provider.py
│   │   └── factory.py
│   ├── storage/               # Storage providers
│   │   ├── base.py
│   │   ├── s3_provider.py
│   │   ├── r2_provider.py
│   │   ├── cloudinary_provider.py
│   │   ├── local_provider.py
│   │   └── factory.py
│   ├── payments/              # Payment providers
│   │   ├── stripe_service.py
│   │   ├── apple_iap_service.py
│   │   ├── google_iap_service.py
│   │   └── usage.py           # Usage tracking service
│   └── websocket/             # WebSocket manager
│       ├── manager.py
│       └── events.py
│
├── jobs/                      # Background Tasks
│   ├── __init__.py            # Enqueue utilities
│   ├── worker.py              # ARQ worker config
│   ├── decorators.py          # @retry, @timeout
│   ├── email_jobs.py          # Email tasks
│   └── report_jobs.py         # Report tasks
│
└── utils/                     # Utility Functions
    ├── __init__.py
    ├── pagination.py          # Pagination helpers
    ├── validators.py          # Input validation
    ├── crypto.py              # Cryptographic utils
    └── resilience.py          # Circuit breaker, retry
```

---

## Naming Conventions

### Files

| Type | Convention | Example |
|------|------------|---------|
| Models | Singular, snake_case | `user.py`, `project.py` |
| Schemas | Same as model | `user.py`, `project.py` |
| Services | Singular + `_service` | `user_service.py` |
| Providers | Provider name + `_provider` | `openai_provider.py` |
| Endpoints | Plural, snake_case | `users.py`, `projects.py` |
| Tests | `test_` + module name | `test_users.py` |

### Classes

| Type | Convention | Example |
|------|------------|---------|
| Models | PascalCase, singular | `User`, `Project` |
| Schemas | PascalCase + action | `UserCreate`, `UserUpdate`, `UserRead` |
| Services | PascalCase + `Service` | `BillingService` |
| Providers | Provider + `Provider` | `OpenAIProvider` |
| Exceptions | PascalCase + `Error` | `NotFoundError` |

### Functions

| Type | Convention | Example |
|------|------------|---------|
| Endpoints | verb_noun (snake_case) | `list_projects`, `create_project` |
| Services | action_object | `get_user`, `create_project` |
| Helpers | descriptive snake_case | `parse_jwt_token` |
| Async | Same + async | `async def get_user()` |

### Variables

| Type | Convention | Example |
|------|------------|---------|
| Local | snake_case | `user_id`, `project_name` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_LIMIT` |
| Private | _underscore prefix | `_cache`, `_pool` |
| Type vars | PascalCase | `ModelType`, `T` |

### Database

| Type | Convention | Example |
|------|------------|---------|
| Table names | Plural, snake_case | `users`, `projects` |
| Column names | snake_case | `created_at`, `owner_id` |
| Foreign keys | referenced_table_id | `user_id`, `project_id` |
| Indexes | table_column_idx | `users_email_idx` |

### API Routes

| Convention | Example |
|------------|---------|
| Plural nouns | `/projects`, `/users` |
| Lowercase, hyphenated | `/billing/checkout` |
| No trailing slash | `/projects` not `/projects/` |
| Resource ID in path | `/projects/{project_id}` |
| Actions as sub-resources | `/users/{id}/deactivate` |

### HTTP Methods

| Method | Purpose | Endpoint Example |
|--------|---------|------------------|
| GET | Read | `GET /projects` |
| POST | Create | `POST /projects` |
| PATCH | Partial update | `PATCH /projects/{id}` |
| DELETE | Remove | `DELETE /projects/{id}` |

> **Note:** We use `PATCH` instead of `PUT` because all update fields are optional.

---

## Request Lifecycle

```
                                    ┌─────────────────────────┐
                                    │    Incoming Request     │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │    CORS Middleware      │
                                    │ (Check allowed origins) │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │  Request ID Middleware  │
                                    │  (Add X-Request-ID)     │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │  Rate Limit Middleware  │
                                    │  (Check/update limits)  │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   Logging Middleware    │
                                    │  (Log request start)    │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │    Route Matching       │
                                    │  (FastAPI router)       │
                                    └───────────┬─────────────┘
                                                │
                              ┌─────────────────┴─────────────────┐
                              │                                   │
                    ┌─────────▼─────────┐              ┌─────────▼─────────┐
                    │  Public Routes    │              │  Protected Routes │
                    │  (No auth)        │              │  (Auth required)  │
                    └─────────┬─────────┘              └─────────┬─────────┘
                              │                                   │
                              │                        ┌──────────▼──────────┐
                              │                        │  JWT Verification   │
                              │                        │  (verify_token)     │
                              │                        └──────────┬──────────┘
                              │                                   │
                              │                        ┌──────────▼──────────┐
                              │                        │  User Resolution    │
                              │                        │  (get_current_user) │
                              │                        └──────────┬──────────┘
                              │                                   │
                              └─────────────────┬─────────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   DB Session Created    │
                                    │   (Dependency)          │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │  Request Validation     │
                                    │  (Pydantic schemas)     │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   Business Logic        │
                                    │   (Service layer)       │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   Database Operations   │
                                    │   (CRUD operations)     │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   Response Serialized   │
                                    │   (Pydantic model)      │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   DB Session Commit     │
                                    │   (Auto on success)     │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │  Security Headers       │
                                    │  (Middleware)           │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   Logging Middleware    │
                                    │   (Log response)        │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   Response Sent         │
                                    └─────────────────────────┘
```

---

## Layer Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Layer (HTTP)                               │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Endpoints (app/api/v1/)                                         │   │
│   │  - Route handlers                                                │   │
│   │  - Request/response serialization                                │   │
│   │  - HTTP-specific logic only                                      │   │
│   └───────────────────────────────┬─────────────────────────────────┘   │
│                                   │                                      │
│   ┌───────────────────────────────▼─────────────────────────────────┐   │
│   │  Dependencies (app/api/deps.py)                                  │   │
│   │  - Authentication                                                │   │
│   │  - Database session                                              │   │
│   │  - Current user resolution                                       │   │
│   └───────────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                         Business Layer (Pure Python)                     │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Services (app/business/)                                        │   │
│   │  - Business rules                                                │   │
│   │  - Orchestration logic                                           │   │
│   │  - No HTTP knowledge                                             │   │
│   └───────────────────────────────┬─────────────────────────────────┘   │
│                                   │                                      │
│   ┌───────────────────────────────▼─────────────────────────────────┐   │
│   │  CRUD Base (app/business/crud_base.py)                           │   │
│   │  - Generic database operations                                   │   │
│   │  - Reusable across models                                        │   │
│   └───────────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                          Data Layer (Database)                           │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Models (app/models/)                                            │   │
│   │  - SQLModel table definitions                                    │   │
│   │  - Database schema                                               │   │
│   └───────────────────────────────┬─────────────────────────────────┘   │
│                                   │                                      │
│   ┌───────────────────────────────▼─────────────────────────────────┐   │
│   │  Database (app/core/db.py)                                       │   │
│   │  - Connection pool                                               │   │
│   │  - Session management                                            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                       External Services (Adapters)                       │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│   │     AI     │  │   Email    │  │  Storage   │  │  Payments  │       │
│   │  Gateway   │  │  Service   │  │  Service   │  │  Service   │       │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

### API Layer (`app/api/`)

**Responsibilities:**
- Route definition
- Request validation (automatic via Pydantic)
- Response serialization
- HTTP status codes
- Dependency injection

**Rules:**
- No business logic
- No direct database queries
- Call services for all operations
- Keep endpoints thin

```python
# Good - thin endpoint
@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    session: DBSession,
    user: CurrentUser,
    project_in: ProjectCreate,
):
    """Create a new project."""
    return await project_service.create_with_owner(
        session, obj_in=project_in, owner_id=user.id
    )

# Bad - business logic in endpoint
@router.post("")
async def create_project(session: DBSession, user: CurrentUser, project_in: ProjectCreate):
    # Don't do this in the endpoint!
    if await session.execute(select(Project).where(Project.name == project_in.name)):
        raise HTTPException(...)
    project = Project(**project_in.model_dump(), owner_id=user.id)
    session.add(project)
    # ...
```

### Business Layer (`app/business/`)

**Responsibilities:**
- Business rules and validation
- Orchestration of operations
- Transaction boundaries
- Domain-specific logic

**Rules:**
- No HTTP concepts (status codes, requests)
- Can call other services
- Can use external service adapters
- Raise domain exceptions, not HTTP exceptions

```python
# Good - pure business logic
class ProjectService(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    async def create_with_owner(
        self,
        session: AsyncSession,
        *,
        obj_in: ProjectCreate,
        owner_id: str,
    ) -> Project:
        """Create project with ownership."""
        return await super().create_with_owner(session, obj_in=obj_in, owner_id=owner_id)

    async def get_active_by_owner(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """Get non-deleted projects for owner."""
        result = await session.execute(
            select(self.model)
            .where(self.model.owner_id == owner_id)
            .where(self.model.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
```

### Data Layer (`app/models/`)

**Responsibilities:**
- Database schema definition
- Relationships
- Table constraints

**Rules:**
- No business logic
- Only data structure definition
- Use SQLModel for type safety

```python
# Model definition
class Project(BaseModel, SoftDeleteMixin, table=True):
    __tablename__ = "projects"

    name: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None, max_length=2000)
    owner_id: str = Field(foreign_key="users.id", index=True)
```

---

## Database Patterns

### Base Model

All models inherit from `BaseModel`:

```python
class BaseModel(SQLModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Soft Delete

Models with `SoftDeleteMixin` are never actually deleted:

```python
class SoftDeleteMixin(SQLModel):
    deleted_at: datetime | None = Field(default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

**Always filter out deleted records:**

```python
# In queries
.where(Model.deleted_at.is_(None))

# In service
await project_service.soft_delete(session, id=project_id)
```

### Generic CRUD

Use `CRUDBase` for common operations:

```python
from app.business.crud_base import CRUDBase

class ProjectService(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    pass

project_service = ProjectService(Project)

# Available methods:
await project_service.get(session, id=id)
await project_service.get_multi(session, skip=0, limit=20)
await project_service.get_multi_by_owner(session, owner_id=user.id)
await project_service.create(session, obj_in=create_schema)
await project_service.create_with_owner(session, obj_in=schema, owner_id=user.id)
await project_service.update(session, db_obj=project, obj_in=update_schema)
await project_service.delete(session, id=id)
await project_service.soft_delete(session, id=id)
await project_service.restore(session, id=id)
```

### Session Management

Database sessions are automatically managed:

```python
@router.get("")
async def list_items(session: DBSession):
    # Session auto-commits on success
    # Session auto-rollbacks on exception
    items = await item_service.get_multi(session)
    return items
```

---

## Authentication Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │     │  Auth Provider  │     │    Backend      │
│   (React/Vue)   │     │ (Supabase/Clerk)│     │   (FastAPI)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  1. Login             │                       │
         │──────────────────────>│                       │
         │                       │                       │
         │  2. JWT Token         │                       │
         │<──────────────────────│                       │
         │                       │                       │
         │  3. API Request       │                       │
         │  Authorization: Bearer <token>                │
         │──────────────────────────────────────────────>│
         │                       │                       │
         │                       │  4. Verify JWT        │
         │                       │<──────────────────────│
         │                       │  (via JWKS)           │
         │                       │──────────────────────>│
         │                       │                       │
         │                       │                       │ 5. Get/Create User
         │                       │                       │    (from DB)
         │                       │                       │
         │  6. Response          │                       │
         │<──────────────────────────────────────────────│
         │                       │                       │
```

### Code Flow

```python
# 1. Dependency injection in endpoint
@router.get("/me")
async def get_me(
    session: DBSession,          # Database session
    user: CurrentUser,            # Resolved user object
) -> UserRead:
    return user

# 2. CurrentUser dependency chain
CurrentUser = Annotated[User, Depends(get_current_user)]

# 3. get_current_user resolution
async def get_current_user(
    session: DBSession,
    user_id: CurrentUserId,      # From JWT 'sub' claim
    payload: TokenPayload,        # Full JWT payload
) -> User:
    user = await sync_user_from_token(session, user_id, payload)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User deactivated")
    return user

# 4. Token verification
def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    token = credentials.credentials
    # Verify with JWKS (RS256) or secret (HS256)
    payload = jwt.decode(token, key=key, algorithms=[algorithm])
    return payload
```

---

## Error Handling

### Custom Exceptions

```python
# Define in app/core/exceptions.py
class NotFoundError(AppException):
    def __init__(self, resource: str, id: str):
        super().__init__(
            message=f"{resource} not found",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": id},
        )

# Use in service/endpoint
raise NotFoundError("Project", project_id)
```

### Exception Handler

Global handler converts exceptions to JSON:

```python
# Returns:
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Project not found",
    "details": {"resource": "Project", "id": "123"}
  }
}
```

### Exception Types

| Exception | Status | When to Use |
|-----------|--------|-------------|
| `NotFoundError` | 404 | Resource doesn't exist |
| `ValidationError` | 422 | Invalid input data |
| `AuthenticationError` | 401 | Missing/invalid token |
| `AuthorizationError` | 403 | Insufficient permissions |
| `ConflictError` | 409 | Duplicate entry |
| `RateLimitError` | 429 | Too many requests |
| `ExternalServiceError` | 502 | External API failed |
| `ServiceUnavailableError` | 503 | Service not configured |

---

## Service Adapters

### Pattern: Abstract Interface + Implementations

```python
# 1. Abstract base (app/services/email/base.py)
class BaseEmailService(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, template: str, data: dict) -> bool:
        pass

# 2. Implementation (app/services/email/resend_provider.py)
class ResendEmailService(BaseEmailService):
    async def send(self, to: str, subject: str, template: str, data: dict) -> bool:
        # Resend-specific implementation
        ...

# 3. Factory (app/services/email/factory.py)
@lru_cache(maxsize=1)
def get_email_service() -> BaseEmailService:
    if settings.EMAIL_PROVIDER == "resend":
        return ResendEmailService()
    elif settings.EMAIL_PROVIDER == "sendgrid":
        return SendGridEmailService()
    return ConsoleEmailService()  # Default fallback
```

### Available Service Adapters

| Service | Providers | Config |
|---------|-----------|--------|
| Email | Resend, SendGrid, Console | `EMAIL_PROVIDER` |
| Storage | S3, R2, Cloudinary, Local | `STORAGE_PROVIDER` |
| AI | OpenAI, Anthropic, Gemini | `AI_DEFAULT_PROVIDER` |
| Payments | Stripe, Apple IAP, Google Play | N/A |

---

## Observability

### Components

| Component | Purpose | Module |
|-----------|---------|--------|
| **Logging** | Structured JSON logs with request context | `app/core/logging.py` |
| **Tracing** | Distributed tracing with OpenTelemetry | `app/core/tracing.py` |
| **Metrics** | Prometheus metrics for monitoring | `app/core/metrics.py` |
| **Error Tracking** | Exception tracking with Sentry | `app/core/sentry.py` |

### Distributed Tracing (OpenTelemetry)

Tracing is integrated at multiple levels:

```
Request Flow with Tracing:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│  FastAPI    │───▶│  Database   │───▶│  External   │
│  (trace_id) │    │  (span)     │    │  (span)     │    │  (span)     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   Redis     │
                   │   (span)    │
                   └─────────────┘
```

**Auto-instrumented:**
- FastAPI HTTP requests
- SQLAlchemy database queries
- Redis operations
- httpx external calls

**Manual tracing:**

```python
from app.core.tracing import create_span, trace_function, set_span_attribute

# Context manager
with create_span("process_payment", {"order_id": order_id}):
    set_span_attribute("amount", amount)
    # ... processing logic

# Decorator
@trace_function("send_notification")
async def send_notification(user_id: str, message: str):
    ...
```

### Log Correlation

All logs include trace context when OpenTelemetry is enabled:

```json
{
  "timestamp": "2026-01-11T12:00:00Z",
  "level": "INFO",
  "message": "Order processed",
  "trace_id": "abc123def456...",
  "span_id": "1234567890ab",
  "request_id": "550e8400-..."
}
```

### Prometheus Metrics

Comprehensive metrics are collected via `app/core/metrics.py`:

```
Metrics Categories:
┌─────────────────────────────────────────────────────────────┐
│                      HTTP Requests                          │
│  - http_requests_total{method, endpoint, status_code}       │
│  - http_request_duration_seconds{method, endpoint}          │
│  - http_requests_in_progress{method, endpoint}              │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Database                               │
│  - db_queries_total{operation, table}                       │
│  - db_query_duration_seconds{operation, table}              │
│  - db_pool_connections{state}                               │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      System                                 │
│  - process_memory_bytes{type}                               │
│  - process_cpu_seconds_total{mode}                          │
│  - app_uptime_seconds                                       │
└─────────────────────────────────────────────────────────────┘
```

**MetricsMiddleware:**

Automatic request tracking with path normalization:

```python
from app.core.metrics import MetricsMiddleware
app.add_middleware(MetricsMiddleware)

# Path normalization examples:
# /api/v1/users/550e8400-e29b-... → /api/v1/users/{id}
# /api/v1/projects/42 → /api/v1/projects/{id}
```

**Recording custom metrics:**

```python
from app.core.metrics import (
    record_auth_event,
    record_rate_limit_hit,
    record_websocket_message,
    record_webhook_event,
)

# Authentication events
record_auth_event("login", provider="jwt")
record_auth_failure("expired_token")

# Rate limiting
record_rate_limit_hit("/api/v1/ai/chat", "user")

# WebSocket messages
record_websocket_message("sent", "message")

# Webhook processing
record_webhook_event("stripe", "invoice.paid", "processed", duration=0.05)
```

### Grafana Dashboards

Pre-built dashboards are available in `grafana/dashboards/`:

| Dashboard | Description |
|-----------|-------------|
| `api-overview.json` | Request rate, latency, errors, top endpoints |
| `database-redis.json` | Connection pools, query performance, cache stats |
| `business-metrics.json` | Users, subscriptions, background jobs, AI usage |

See `grafana/README.md` for installation instructions.

### Usage Tracking

The usage tracking system monitors API calls, AI tokens, storage, and other metrics for billing and analytics.

```
Usage Tracking Flow:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Request   │───▶│  Middleware │───▶│   Redis     │
│             │    │  (track)    │    │  (counters) │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  PostgreSQL │
                   │  (persist)  │
                   └─────────────┘
```

**Tracked Metrics:**

| Metric | Description | Tracked By |
|--------|-------------|------------|
| `api_requests` | API request count | UsageTrackingMiddleware |
| `ai_tokens` | AI/LLM tokens consumed | AI endpoints |
| `ai_requests` | AI completion requests | AI endpoints |
| `storage_bytes` | Storage space used | File uploads |
| `file_uploads` | Files uploaded | File endpoints |
| `file_downloads` | Files downloaded | File endpoints |
| `websocket_messages` | WebSocket messages | WebSocket manager |
| `background_jobs` | Jobs executed | Job worker |
| `email_sent` | Emails sent | Email service |

**Usage Example:**

```python
from app.services.payments.usage import get_usage_tracker, track_ai_usage

# Get tracker instance
tracker = get_usage_tracker()

# Track custom metric
await tracker.track("custom_metric", user_id, amount=1)

# Track AI usage (called automatically by AI endpoints)
await track_ai_usage(
    user_id="user_123",
    model="gpt-4o",
    prompt_tokens=100,
    completion_tokens=200,
)

# Get usage summary
summary = await tracker.get_usage_summary(user_id, period_start, period_end)
```

---

## Database Compatibility

### SQLite Fallback

The application supports SQLite for offline development without Docker:

```python
# app/models/compat.py - Cross-database column helpers

from app.models.compat import JSONColumn, ArrayColumn

class MyModel(BaseModel, table=True):
    # Uses JSONB on PostgreSQL, JSON on SQLite
    metadata: dict = Field(sa_column=JSONColumn())

    # Uses ARRAY on PostgreSQL, JSON on SQLite
    tags: list[str] = Field(sa_column=ArrayColumn(String))
```

**Database Detection:**

```python
from app.core.config import settings

if settings.is_sqlite:
    # SQLite-specific logic
    ...
else:
    # PostgreSQL-specific logic
    ...
```

**In-Memory Cache Fallback:**

When Redis is unavailable, the cache automatically falls back to in-memory storage:

```python
from app.core.cache import get_cache

cache = get_cache()  # Returns Redis or InMemoryCache

# Same API for both
await cache.set("key", "value", ttl=300)
value = await cache.get("key")
```

> **Note:** SQLite and in-memory cache are for development only. Use PostgreSQL and Redis in production.

---

## Adding New Features

### Adding a New Endpoint

1. **Create/update schema** (`app/schemas/`)
2. **Create/update model** if needed (`app/models/`)
3. **Create/update service** (`app/business/`)
4. **Create endpoint** (`app/api/v1/`)
5. **Register router** (`app/api/v1/router.py`)
6. **Add tests** (`tests/`)

### Example: Adding a "Task" Resource

```python
# 1. Model (app/models/task.py)
class Task(BaseModel, SoftDeleteMixin, table=True):
    __tablename__ = "tasks"
    title: str = Field(max_length=255)
    completed: bool = Field(default=False)
    project_id: str = Field(foreign_key="projects.id")

# 2. Schema (app/schemas/task.py)
class TaskCreate(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    project_id: str

class TaskUpdate(SQLModel):
    title: str | None = None
    completed: bool | None = None

class TaskRead(SQLModel):
    id: str
    title: str
    completed: bool
    project_id: str
    created_at: datetime

# 3. Service (app/business/task_service.py)
class TaskService(CRUDBase[Task, TaskCreate, TaskUpdate]):
    async def get_by_project(
        self, session: AsyncSession, *, project_id: str
    ) -> list[Task]:
        result = await session.execute(
            select(self.model).where(self.model.project_id == project_id)
        )
        return list(result.scalars().all())

task_service = TaskService(Task)

# 4. Endpoint (app/api/v1/app/tasks.py)
router = APIRouter(tags=["Tasks"])

@router.get("", response_model=list[TaskRead])
async def list_tasks(
    session: DBSession,
    user: CurrentUser,
    project_id: str = Query(...),
):
    # Verify user owns project
    project = await project_service.get(session, id=project_id)
    if not project or project.owner_id != user.id:
        raise NotFoundError("Project", project_id)

    return await task_service.get_by_project(session, project_id=project_id)

# 5. Register (app/api/v1/router.py)
from app.api.v1.app import tasks
app_router.include_router(tasks.router, prefix="/tasks")
```

### Adding a New External Service

1. **Create base interface** (`app/services/myservice/base.py`)
2. **Create implementations** (`app/services/myservice/provider.py`)
3. **Create factory** (`app/services/myservice/factory.py`)
4. **Add config** (`app/core/config.py`)
5. **Document** environment variables

---

## CI/CD Pipelines

### CI Pipeline (`.github/workflows/ci.yml`)

```yaml
Jobs:
1. Lint (ruff check, ruff format)
2. Type check (mypy)
3. Unit tests (pytest tests/unit)
4. Integration tests (pytest tests/integration)
5. Build Docker image
6. Security scan (bandit)
```

### Deploy Pipeline (`.github/workflows/deploy.yml`)

```yaml
Stages:
1. Build → Push to registry
2. Deploy to staging
3. Run smoke tests
4. Deploy to production
5. Create Sentry release
6. Notify Slack
```

---

## Best Practices Summary

### Do

- Use type hints everywhere
- Keep endpoints thin (delegate to services)
- Use dependency injection
- Write async code for all I/O
- Add docstrings to public functions
- Follow naming conventions
- Write tests for new features

### Don't

- Put business logic in endpoints
- Use synchronous database calls
- Hardcode configuration values
- Commit secrets to git
- Skip input validation
- Ignore error handling
- Create god classes/functions
