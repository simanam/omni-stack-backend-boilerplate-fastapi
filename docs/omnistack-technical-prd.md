# OmniStack Backend — Technical PRD

**Version:** 1.0  
**Last Updated:** January 2026  
**Target Stack:** Python 3.12+ | FastAPI 0.115+ | SQLModel | PostgreSQL 16+ | Redis 7+

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [Configuration System](#3-configuration-system)
4. [Database Layer](#4-database-layer)
5. [Authentication System](#5-authentication-system)
6. [Rate Limiting](#6-rate-limiting)
7. [Background Jobs](#7-background-jobs)
8. [AI Gateway](#8-ai-gateway)
9. [External Service Adapters](#9-external-service-adapters)
10. [API Design Patterns](#10-api-design-patterns)
11. [Error Handling](#11-error-handling)
12. [Testing Strategy](#12-testing-strategy)
13. [Deployment](#13-deployment)
14. [Security Checklist](#14-security-checklist)

---

## 1. Architecture Overview

### Design Principles

1. **12-Factor App Compliance** — All configuration via environment variables
2. **Adapter Pattern** — External services are plugins, not dependencies
3. **Clean Architecture** — Business logic has zero knowledge of HTTP
4. **Async-First** — All I/O operations are non-blocking
5. **Fail-Fast** — Invalid config fails at startup, not runtime

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│                    (FastAPI Application)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Public     │  │     App      │  │    Admin     │          │
│  │   Routes     │  │   Routes     │  │   Routes     │          │
│  │  /api/v1/    │  │  /api/v1/    │  │  /api/v1/    │          │
│  │   public/    │  │    app/      │  │   admin/     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └────────────────┬┴─────────────────┘                    │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────────────────┐  │
│  │                  Dependency Layer                          │  │
│  │   (Auth Verification, DB Session, Rate Limiter, Cache)    │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────────────────┐  │
│  │                  Business Logic Layer                      │  │
│  │      (Pure Python - No HTTP, No Framework Knowledge)       │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────────────────┐  │
│  │                   Service Adapters                         │  │
│  │    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │  │
│  │    │  Auth   │ │   AI    │ │  Email  │ │ Storage │       │  │
│  │    │ Adapter │ │ Gateway │ │ Service │ │ Service │       │  │
│  │    └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │  │
│  │         │           │           │           │             │  │
│  └─────────┼───────────┼───────────┼───────────┼─────────────┘  │
│            │           │           │           │                 │
└────────────┼───────────┼───────────┼───────────┼─────────────────┘
             │           │           │           │
    ┌────────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
    │ Clerk/      │ │ OpenAI/ │ │ Resend/ │ │  S3/    │
    │ Supabase    │ │ Claude  │ │ SendGrid│ │  R2     │
    └─────────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Request Lifecycle

```
1. Request arrives at FastAPI
2. Middleware runs (CORS, Rate Limit Check, Request ID)
3. Route matched, dependencies resolved
4. Auth verified (if protected route)
5. DB session created
6. Business logic executed
7. Response serialized
8. Middleware post-processing (logging, metrics)
9. Response sent
```

---

## 2. Project Structure

```
omnistack/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application factory
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # Dependency injection (auth, db, cache)
│   │   │
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # Aggregates all v1 routers
│   │       │
│   │       ├── public/            # No auth required
│   │       │   ├── __init__.py
│   │       │   ├── health.py      # Health check endpoints
│   │       │   ├── webhooks.py    # Stripe, Clerk webhooks
│   │       │   └── contact.py     # Contact form
│   │       │
│   │       ├── app/               # Auth required
│   │       │   ├── __init__.py
│   │       │   ├── users.py       # User profile endpoints
│   │       │   ├── projects.py    # Example resource CRUD
│   │       │   └── ai.py          # AI completion endpoints
│   │       │
│   │       └── admin/             # Auth + Admin role required
│   │           ├── __init__.py
│   │           ├── users.py       # User management
│   │           ├── jobs.py        # Background job monitoring
│   │           └── metrics.py     # System metrics
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings
│   │   ├── security.py            # JWT verification
│   │   ├── db.py                  # Database engine & session
│   │   ├── cache.py               # Redis client
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── middleware.py          # CORS, logging, rate limit
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # Base SQLModel with common fields
│   │   ├── user.py                # User model
│   │   └── project.py             # Example resource model
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py                # User request/response schemas
│   │   ├── project.py             # Project schemas
│   │   └── common.py              # Shared schemas (pagination, etc.)
│   │
│   ├── services/                  # External service adapters
│   │   ├── __init__.py
│   │   │
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract LLM interface
│   │   │   ├── openai.py          # OpenAI implementation
│   │   │   ├── anthropic.py       # Anthropic implementation
│   │   │   ├── factory.py         # Returns correct client
│   │   │   └── router.py          # Smart model routing
│   │   │
│   │   ├── email/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract email interface
│   │   │   ├── resend.py          # Resend implementation
│   │   │   ├── sendgrid.py        # SendGrid implementation
│   │   │   └── factory.py         # Returns correct client
│   │   │
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract storage interface
│   │   │   ├── s3.py              # AWS S3 implementation
│   │   │   ├── r2.py              # Cloudflare R2 implementation
│   │   │   └── factory.py         # Returns correct client
│   │   │
│   │   └── payments/
│   │       ├── __init__.py
│   │       └── stripe.py          # Stripe service
│   │
│   ├── business/                  # Pure business logic (no HTTP)
│   │   ├── __init__.py
│   │   ├── user_service.py        # User operations
│   │   ├── project_service.py     # Project operations
│   │   └── billing_service.py     # Subscription logic
│   │
│   ├── jobs/                      # Background tasks (ARQ)
│   │   ├── __init__.py
│   │   ├── worker.py              # ARQ worker config
│   │   ├── email_jobs.py          # Email sending tasks
│   │   └── report_jobs.py         # Report generation tasks
│   │
│   └── utils/
│       ├── __init__.py
│       ├── pagination.py          # Pagination helpers
│       ├── validators.py          # Custom validators
│       └── crypto.py              # Hashing, encryption helpers
│
├── migrations/                    # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── factories/                 # Test data factories
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── e2e/                       # End-to-end tests
│
├── scripts/
│   ├── seed.py                    # Database seeding
│   └── migrate.py                 # Migration runner
│
├── docker/
│   ├── Dockerfile                 # Production image
│   ├── Dockerfile.dev             # Development image
│   └── docker-compose.yml         # Local services
│
├── .env.example                   # Environment template
├── .env.local                     # Local overrides (gitignored)
├── .env.test                      # Test environment
├── alembic.ini                    # Alembic config
├── pyproject.toml                 # Python dependencies
├── Makefile                       # Developer commands
├── railway.toml                   # Railway deployment
├── render.yaml                    # Render deployment
└── README.md                      # Getting started guide
```

---

## 3. Configuration System

### Environment Variables Contract

```ini
# ============================================
# CORE SETTINGS
# ============================================
PROJECT_NAME="My SaaS"
ENVIRONMENT="local"                    # local | staging | production
DEBUG="true"                           # Enable debug mode
LOG_LEVEL="INFO"                       # DEBUG | INFO | WARNING | ERROR

# ============================================
# API SETTINGS
# ============================================
API_V1_STR="/api/v1"
BACKEND_CORS_ORIGINS='["http://localhost:3000","https://myapp.com"]'
SECRET_KEY="your-secret-key-min-32-chars"

# ============================================
# DATABASE
# ============================================
DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/omnistack"
# For serverless (Neon, Supabase), add these:
DB_POOL_SIZE="5"                       # Reduce for serverless
DB_POOL_RECYCLE="300"                  # Recycle connections after 5 min
DB_USE_NULL_POOL="false"               # Set "true" for serverless

# ============================================
# REDIS / CACHE
# ============================================
REDIS_URL="redis://localhost:6379/0"
# For Upstash (HTTP mode):
UPSTASH_REDIS_REST_URL=""
UPSTASH_REDIS_REST_TOKEN=""

# ============================================
# AUTHENTICATION
# ============================================
AUTH_PROVIDER="supabase"               # supabase | clerk | custom

# Supabase Auth
SUPABASE_PROJECT_URL="https://xxx.supabase.co"
SUPABASE_JWT_SECRET=""                 # Only for legacy HS256

# Clerk Auth
CLERK_ISSUER_URL="https://xxx.clerk.accounts.dev"
CLERK_SECRET_KEY=""                    # For backend operations

# Custom OAuth
OAUTH_JWKS_URL=""
OAUTH_AUDIENCE=""
OAUTH_ISSUER=""

# ============================================
# AI PROVIDERS
# ============================================
AI_DEFAULT_PROVIDER="openai"           # openai | anthropic
AI_DEFAULT_MODEL="gpt-4o"

OPENAI_API_KEY=""
ANTHROPIC_API_KEY=""
PERPLEXITY_API_KEY=""

# ============================================
# EMAIL
# ============================================
EMAIL_PROVIDER="resend"                # resend | sendgrid
EMAIL_FROM_ADDRESS="hello@myapp.com"
EMAIL_FROM_NAME="My SaaS"

RESEND_API_KEY=""
SENDGRID_API_KEY=""

# ============================================
# STORAGE
# ============================================
STORAGE_PROVIDER="s3"                  # s3 | r2 | local

# AWS S3
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_REGION="us-east-1"
AWS_S3_BUCKET=""

# Cloudflare R2
R2_ACCOUNT_ID=""
R2_ACCESS_KEY_ID=""
R2_SECRET_ACCESS_KEY=""
R2_BUCKET=""

# ============================================
# PAYMENTS (STRIPE)
# ============================================
STRIPE_SECRET_KEY=""
STRIPE_WEBHOOK_SECRET=""
STRIPE_PRICE_ID_MONTHLY=""
STRIPE_PRICE_ID_YEARLY=""

# ============================================
# OBSERVABILITY
# ============================================
SENTRY_DSN=""
SENTRY_TRACES_SAMPLE_RATE="0.1"        # 10% of requests traced

# ============================================
# RATE LIMITING
# ============================================
RATE_LIMIT_DEFAULT="60/minute"
RATE_LIMIT_AI="10/minute"
RATE_LIMIT_AUTH="5/minute"
```

### Configuration Class (`app/core/config.py`)

```python
from typing import Literal, Optional, List
from pydantic import Field, computed_field, field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All external service configurations are optional to support incremental setup.
    """
    
    # --- Core ---
    PROJECT_NAME: str = "OmniStack API"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    SECRET_KEY: str = Field(..., min_length=32)
    
    # --- API ---
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: str = '["http://localhost:3000"]'
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v  # Keep as string, parse in computed_field
    
    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        return json.loads(self.BACKEND_CORS_ORIGINS)
    
    # --- Database ---
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_POOL_RECYCLE: int = 3600
    DB_USE_NULL_POOL: bool = False  # True for serverless (Neon, Supabase)
    
    @computed_field
    @property
    def async_database_url(self) -> str:
        """Ensure we're using asyncpg driver."""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
    
    # --- Redis ---
    REDIS_URL: Optional[str] = None
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None
    
    @computed_field
    @property
    def redis_available(self) -> bool:
        return bool(self.REDIS_URL or self.UPSTASH_REDIS_REST_URL)
    
    # --- Authentication ---
    AUTH_PROVIDER: Literal["supabase", "clerk", "custom"] = "supabase"
    
    # Supabase
    SUPABASE_PROJECT_URL: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None  # Legacy HS256
    
    # Clerk
    CLERK_ISSUER_URL: Optional[str] = None
    CLERK_SECRET_KEY: Optional[str] = None
    
    # Custom OAuth
    OAUTH_JWKS_URL: Optional[str] = None
    OAUTH_AUDIENCE: Optional[str] = None
    OAUTH_ISSUER: Optional[str] = None
    
    @computed_field
    @property
    def jwks_url(self) -> Optional[str]:
        """Auto-generate JWKS URL based on provider."""
        if self.AUTH_PROVIDER == "clerk" and self.CLERK_ISSUER_URL:
            return f"{self.CLERK_ISSUER_URL.rstrip('/')}/.well-known/jwks.json"
        if self.AUTH_PROVIDER == "supabase" and self.SUPABASE_PROJECT_URL:
            return f"{self.SUPABASE_PROJECT_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        if self.AUTH_PROVIDER == "custom" and self.OAUTH_JWKS_URL:
            return self.OAUTH_JWKS_URL
        return None
    
    @computed_field
    @property
    def jwt_algorithm(self) -> str:
        """Determine JWT algorithm based on provider config."""
        if self.AUTH_PROVIDER == "supabase" and self.SUPABASE_JWT_SECRET:
            return "HS256"  # Legacy Supabase
        return "RS256"  # Modern default
    
    # --- AI ---
    AI_DEFAULT_PROVIDER: Literal["openai", "anthropic"] = "openai"
    AI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    
    @computed_field
    @property
    def ai_available(self) -> bool:
        return bool(self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY)
    
    # --- Email ---
    EMAIL_PROVIDER: Literal["resend", "sendgrid", "console"] = "console"
    EMAIL_FROM_ADDRESS: str = "hello@example.com"
    EMAIL_FROM_NAME: str = "My App"
    RESEND_API_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    
    # --- Storage ---
    STORAGE_PROVIDER: Literal["s3", "r2", "local"] = "local"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET: Optional[str] = None
    
    # --- Stripe ---
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID_MONTHLY: Optional[str] = None
    STRIPE_PRICE_ID_YEARLY: Optional[str] = None
    
    @computed_field
    @property
    def stripe_available(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)
    
    # --- Observability ---
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # --- Rate Limiting ---
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AI: str = "10/minute"
    RATE_LIMIT_AUTH: str = "5/minute"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra env vars
    )


# Singleton instance
settings = Settings()
```

---

## 4. Database Layer

### Connection Management (`app/core/db.py`)

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlmodel import SQLModel

from app.core.config import settings


def get_pool_class():
    """Use NullPool for serverless, QueuePool for traditional."""
    if settings.DB_USE_NULL_POOL:
        return NullPool
    return AsyncAdaptedQueuePool


engine = create_async_engine(
    settings.async_database_url,
    poolclass=get_pool_class(),
    pool_size=settings.DB_POOL_SIZE if not settings.DB_USE_NULL_POOL else None,
    pool_recycle=settings.DB_POOL_RECYCLE if not settings.DB_USE_NULL_POOL else None,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Create all tables. Use migrations in production."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for use outside of FastAPI dependencies."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Base Model (`app/models/base.py`)

```python
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func
import uuid


class BaseModel(SQLModel):
    """Base model with common fields for all database tables."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="Unique identifier (UUID)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=func.now()),
        description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()),
        description="Last update timestamp"
    )


class SoftDeleteMixin(SQLModel):
    """Mixin for soft delete support."""
    
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Soft delete timestamp (null = active)"
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

### Generic CRUD Base (`app/business/crud_base.py`)

```python
from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic CRUD operations for any SQLModel.
    
    Usage:
        class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
            pass
        
        user_crud = UserCRUD(User)
        user = await user_crud.get(session, id="123")
    """
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(
        self, 
        session: AsyncSession, 
        id: str
    ) -> Optional[ModelType]:
        """Get single record by ID."""
        result = await session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_field(
        self,
        session: AsyncSession,
        field: str,
        value: Any
    ) -> Optional[ModelType]:
        """Get single record by arbitrary field."""
        result = await session.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        result = await session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def count(self, session: AsyncSession) -> int:
        """Get total count of records."""
        result = await session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
    
    async def create(
        self,
        session: AsyncSession,
        *,
        obj_in: CreateSchemaType
    ) -> ModelType:
        """Create new record."""
        db_obj = self.model.model_validate(obj_in)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        session: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """Update existing record."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def delete(
        self,
        session: AsyncSession,
        *,
        id: str
    ) -> Optional[ModelType]:
        """Hard delete record."""
        obj = await self.get(session, id=id)
        if obj:
            await session.delete(obj)
            await session.flush()
        return obj
    
    async def soft_delete(
        self,
        session: AsyncSession,
        *,
        id: str
    ) -> Optional[ModelType]:
        """Soft delete record (requires SoftDeleteMixin)."""
        from datetime import datetime
        obj = await self.get(session, id=id)
        if obj and hasattr(obj, 'deleted_at'):
            obj.deleted_at = datetime.utcnow()
            session.add(obj)
            await session.flush()
        return obj
```

---

## 5. Authentication System

### Security Module (`app/core/security.py`)

```python
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime, timedelta

from app.core.config import settings

security_scheme = HTTPBearer(
    scheme_name="Bearer Token",
    description="JWT token from your auth provider (Supabase/Clerk)"
)


class AuthError(Exception):
    """Custom auth exception for internal use."""
    pass


@lru_cache(maxsize=1)
def get_jwks_client() -> Optional[PyJWKClient]:
    """
    Cached JWKS client for RS256 verification.
    Returns None if using HS256 (legacy Supabase).
    """
    if settings.jwt_algorithm == "RS256" and settings.jwks_url:
        return PyJWKClient(
            settings.jwks_url,
            cache_keys=True,
            lifespan=3600  # Cache keys for 1 hour
        )
    return None


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme)
) -> Dict[str, Any]:
    """
    Universal JWT verifier for Supabase, Clerk, or custom OAuth.
    
    Returns the decoded payload containing user info.
    Raises 401 if token is invalid.
    """
    token = credentials.credentials
    
    try:
        # Determine signing key based on algorithm
        if settings.jwt_algorithm == "RS256":
            jwks_client = get_jwks_client()
            if not jwks_client:
                raise AuthError("JWKS client not configured")
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
        else:
            # HS256 (legacy Supabase)
            if not settings.SUPABASE_JWT_SECRET:
                raise AuthError("JWT secret not configured")
            key = settings.SUPABASE_JWT_SECRET
        
        # Decode and verify
        payload = jwt.decode(
            token,
            key=key,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_aud": False,  # Audience varies by provider
                "verify_iss": False,  # We handle issuer manually if needed
            }
        )
        
        # Basic validation
        if not payload.get("sub"):
            raise AuthError("Token missing 'sub' claim")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(
    payload: Dict[str, Any] = Depends(verify_token)
) -> str:
    """Extract user ID from verified token."""
    return payload["sub"]


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        def admin_only(): ...
    """
    def role_checker(payload: Dict[str, Any] = Depends(verify_token)):
        # Check common role claim locations
        user_role = (
            payload.get("role") or 
            payload.get("user_role") or
            payload.get("app_metadata", {}).get("role") or
            payload.get("public_metadata", {}).get("role")
        )
        
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return payload
    
    return role_checker


# Convenience dependencies
require_admin = require_role("admin")
```

### User Model with Auth Sync (`app/models/user.py`)

```python
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

from app.models.base import BaseModel


class User(BaseModel, table=True):
    """
    User model synced from auth provider.
    The `id` field should match the `sub` claim from JWT.
    """
    __tablename__ = "users"
    
    # Override id to use auth provider's ID
    id: str = Field(primary_key=True, description="Auth provider user ID (sub claim)")
    
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Role & permissions
    role: str = Field(default="user", description="user | admin | superadmin")
    is_active: bool = Field(default=True)
    
    # Subscription
    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    subscription_status: Optional[str] = Field(default=None)  # active, canceled, past_due
    subscription_plan: Optional[str] = Field(default=None)    # free, pro, enterprise
    
    # Metadata
    last_login_at: Optional[datetime] = None
    login_count: int = Field(default=0)


class UserCreate(SQLModel):
    """Schema for creating a user (typically from webhook)."""
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserUpdate(SQLModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserRead(SQLModel):
    """Schema for API responses."""
    id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    subscription_plan: Optional[str]
    created_at: datetime
```

---

## 6. Rate Limiting

### Rate Limiter (`app/core/middleware.py`)

```python
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict, Tuple
import time
import asyncio
from dataclasses import dataclass

from app.core.config import settings
from app.core.cache import redis_client


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests: int
    window_seconds: int
    
    @classmethod
    def from_string(cls, s: str) -> "RateLimitConfig":
        """Parse '60/minute' format."""
        parts = s.split("/")
        requests = int(parts[0])
        
        window_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        window = window_map.get(parts[1], 60)
        return cls(requests=requests, window_seconds=window)


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    Falls back to in-memory if Redis unavailable.
    """
    
    def __init__(self):
        self._memory_store: Dict[str, list] = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(
        self, 
        key: str, 
        config: RateLimitConfig
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed.
        Returns: (allowed, remaining, reset_time)
        """
        if redis_client:
            return await self._check_redis(key, config)
        return await self._check_memory(key, config)
    
    async def _check_redis(
        self, 
        key: str, 
        config: RateLimitConfig
    ) -> Tuple[bool, int, int]:
        """Redis-backed rate limiting."""
        now = int(time.time())
        window_start = now - config.window_seconds
        redis_key = f"ratelimit:{key}"
        
        pipe = redis_client.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)
        # Add current request
        pipe.zadd(redis_key, {str(now): now})
        # Count requests in window
        pipe.zcard(redis_key)
        # Set expiry
        pipe.expire(redis_key, config.window_seconds)
        
        results = await pipe.execute()
        request_count = results[2]
        
        allowed = request_count <= config.requests
        remaining = max(0, config.requests - request_count)
        reset_time = now + config.window_seconds
        
        return allowed, remaining, reset_time
    
    async def _check_memory(
        self, 
        key: str, 
        config: RateLimitConfig
    ) -> Tuple[bool, int, int]:
        """In-memory fallback (not suitable for multi-process)."""
        async with self._lock:
            now = time.time()
            window_start = now - config.window_seconds
            
            # Clean old entries
            if key in self._memory_store:
                self._memory_store[key] = [
                    t for t in self._memory_store[key] if t > window_start
                ]
            else:
                self._memory_store[key] = []
            
            # Add current request
            self._memory_store[key].append(now)
            request_count = len(self._memory_store[key])
            
            allowed = request_count <= config.requests
            remaining = max(0, config.requests - request_count)
            reset_time = int(now + config.window_seconds)
            
            return allowed, remaining, reset_time


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that applies rate limiting to all routes."""
    
    # Route-specific limits (path prefix -> config string)
    ROUTE_LIMITS = {
        "/api/v1/app/ai": settings.RATE_LIMIT_AI,
        "/api/v1/public/auth": settings.RATE_LIMIT_AUTH,
    }
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready"]:
            return await call_next(request)
        
        # Determine rate limit config
        config_str = settings.RATE_LIMIT_DEFAULT
        for prefix, limit in self.ROUTE_LIMITS.items():
            if request.url.path.startswith(prefix):
                config_str = limit
                break
        
        config = RateLimitConfig.from_string(config_str)
        
        # Build rate limit key (IP + path for unauthenticated, user_id + path for authenticated)
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        
        # Check rate limit
        allowed, remaining, reset_time = await rate_limiter.is_allowed(key, config)
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(config.window_seconds),
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
```

---

## 7. Background Jobs

### ARQ Worker Configuration (`app/jobs/worker.py`)

```python
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker
from typing import Optional
import logging

from app.core.config import settings
from app.core.db import get_session_context

logger = logging.getLogger(__name__)


def get_redis_settings() -> Optional[RedisSettings]:
    """Parse Redis URL into ARQ settings."""
    if not settings.REDIS_URL:
        return None
    
    # Parse redis://user:password@host:port/db
    from urllib.parse import urlparse
    parsed = urlparse(settings.REDIS_URL)
    
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


async def startup(ctx: dict):
    """Called when worker starts."""
    logger.info("ARQ Worker starting up...")
    # You can initialize shared resources here


async def shutdown(ctx: dict):
    """Called when worker shuts down."""
    logger.info("ARQ Worker shutting down...")


class WorkerSettings:
    """ARQ worker configuration."""
    
    redis_settings = get_redis_settings()
    
    # Import all job functions
    functions = [
        # Email jobs
        "app.jobs.email_jobs.send_welcome_email",
        "app.jobs.email_jobs.send_password_reset_email",
        
        # Report jobs
        "app.jobs.report_jobs.generate_daily_report",
        "app.jobs.report_jobs.export_user_data",
    ]
    
    # Cron jobs (scheduled tasks)
    cron_jobs = [
        # Daily report at 9am UTC
        {
            "coroutine": "app.jobs.report_jobs.generate_daily_report",
            "hour": 9,
            "minute": 0,
        },
    ]
    
    on_startup = startup
    on_shutdown = shutdown
    
    # Worker settings
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # Keep results for 1 hour
    poll_delay = 0.5
```

### Email Jobs (`app/jobs/email_jobs.py`)

```python
from typing import Dict, Any
import logging

from app.services.email.factory import get_email_service

logger = logging.getLogger(__name__)


async def send_welcome_email(ctx: dict, user_email: str, user_name: str):
    """Send welcome email to new user."""
    email_service = get_email_service()
    
    try:
        await email_service.send(
            to=user_email,
            subject="Welcome to OmniStack!",
            template="welcome",
            data={"name": user_name}
        )
        logger.info(f"Welcome email sent to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")
        raise


async def send_password_reset_email(ctx: dict, user_email: str, reset_link: str):
    """Send password reset email."""
    email_service = get_email_service()
    
    try:
        await email_service.send(
            to=user_email,
            subject="Reset Your Password",
            template="password_reset",
            data={"reset_link": reset_link}
        )
        logger.info(f"Password reset email sent to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        raise
```

### Enqueuing Jobs (`app/jobs/__init__.py`)

```python
from arq import create_pool
from typing import Optional
import logging

from app.jobs.worker import get_redis_settings

logger = logging.getLogger(__name__)

_pool = None


async def get_job_pool():
    """Get or create ARQ connection pool."""
    global _pool
    
    redis_settings = get_redis_settings()
    if not redis_settings:
        logger.warning("Redis not configured, jobs will not be queued")
        return None
    
    if _pool is None:
        _pool = await create_pool(redis_settings)
    
    return _pool


async def enqueue(
    function_name: str,
    *args,
    _job_id: Optional[str] = None,
    _defer_by: Optional[int] = None,
    **kwargs
):
    """
    Enqueue a background job.
    
    Usage:
        await enqueue("app.jobs.email_jobs.send_welcome_email", "user@example.com", "John")
    """
    pool = await get_job_pool()
    
    if pool is None:
        # Fallback: execute synchronously (for development)
        logger.warning(f"Executing {function_name} synchronously (no Redis)")
        # Import and call the function directly
        module_path, func_name = function_name.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        return await func({}, *args, **kwargs)
    
    return await pool.enqueue_job(
        function_name,
        *args,
        _job_id=_job_id,
        _defer_by=_defer_by,
        **kwargs
    )
```

---

## 8. AI Gateway

### LLM Interface (`app/services/ai/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class ModelComplexity(Enum):
    """Task complexity for smart routing."""
    SIMPLE = "simple"      # Classification, extraction, simple Q&A
    MODERATE = "moderate"  # Summarization, basic analysis
    COMPLEX = "complex"    # Reasoning, coding, creative writing
    SEARCH = "search"      # Requires current information


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: str
    latency_ms: float


@dataclass
class Message:
    """Chat message."""
    role: str  # system, user, assistant
    content: str


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    provider_name: str
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate completion."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion."""
        pass
```

### OpenAI Provider (`app/services/ai/openai.py`)

```python
import time
from typing import List, AsyncGenerator
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, LLMResponse, Message


class OpenAIProvider(BaseLLMProvider):
    """OpenAI/GPT provider implementation."""
    
    provider_name = "openai"
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def complete(
        self,
        messages: List[Message],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        start_time = time.time()
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
            latency_ms=latency_ms,
        )
    
    async def stream(
        self,
        messages: List[Message],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

### Smart Router (`app/services/ai/router.py`)

```python
from typing import List, Optional
from dataclasses import dataclass

from app.core.config import settings
from app.services.ai.base import ModelComplexity, Message, LLMResponse
from app.services.ai.factory import get_llm_provider


@dataclass
class ModelConfig:
    """Model routing configuration."""
    provider: str
    model: str
    cost_per_1k_tokens: float


# Model routing table
MODEL_ROUTES = {
    ModelComplexity.SIMPLE: ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        cost_per_1k_tokens=0.00015
    ),
    ModelComplexity.MODERATE: ModelConfig(
        provider="openai",
        model="gpt-4o",
        cost_per_1k_tokens=0.0025
    ),
    ModelComplexity.COMPLEX: ModelConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        cost_per_1k_tokens=0.003
    ),
    ModelComplexity.SEARCH: ModelConfig(
        provider="perplexity",
        model="llama-3.1-sonar-large-128k-online",
        cost_per_1k_tokens=0.001
    ),
}


class LLMRouter:
    """
    Smart LLM router that selects the best model based on task complexity.
    """
    
    async def complete(
        self,
        prompt: str,
        complexity: ModelComplexity = ModelComplexity.MODERATE,
        system_prompt: Optional[str] = None,
        override_model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Route completion to appropriate model.
        
        Args:
            prompt: User prompt
            complexity: Task complexity for routing
            system_prompt: Optional system message
            override_model: Force specific model (bypasses routing)
        """
        # Build messages
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        
        # Get model config
        config = MODEL_ROUTES[complexity]
        
        # Override if specified
        if override_model:
            model = override_model
            provider_name = settings.AI_DEFAULT_PROVIDER
        else:
            model = config.model
            provider_name = config.provider
        
        # Get provider and complete
        provider = get_llm_provider(provider_name)
        return await provider.complete(messages, model=model, **kwargs)
    
    async def chat(
        self,
        messages: List[Message],
        complexity: ModelComplexity = ModelComplexity.MODERATE,
        **kwargs
    ) -> LLMResponse:
        """
        Multi-turn chat completion.
        """
        config = MODEL_ROUTES[complexity]
        provider = get_llm_provider(config.provider)
        return await provider.complete(messages, model=config.model, **kwargs)


# Singleton
llm_router = LLMRouter()
```

---

## 9. External Service Adapters

### Email Service Interface (`app/services/email/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BaseEmailService(ABC):
    """Abstract email service interface."""
    
    @abstractmethod
    async def send(
        self,
        to: str | List[str],
        subject: str,
        template: str,
        data: Dict[str, Any],
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> bool:
        """Send templated email."""
        pass
    
    @abstractmethod
    async def send_raw(
        self,
        to: str | List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send raw HTML email."""
        pass
```

### Resend Implementation (`app/services/email/resend.py`)

```python
import resend
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.services.email.base import BaseEmailService


# Email templates (in production, use a template engine)
TEMPLATES = {
    "welcome": """
        <h1>Welcome, {name}!</h1>
        <p>Thanks for joining OmniStack.</p>
    """,
    "password_reset": """
        <h1>Reset Your Password</h1>
        <p>Click <a href="{reset_link}">here</a> to reset your password.</p>
    """,
}


class ResendEmailService(BaseEmailService):
    """Resend email service implementation."""
    
    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY
    
    async def send(
        self,
        to: str | List[str],
        subject: str,
        template: str,
        data: Dict[str, Any],
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> bool:
        html_content = TEMPLATES.get(template, "").format(**data)
        return await self.send_raw(to, subject, html_content)
    
    async def send_raw(
        self,
        to: str | List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        try:
            from_address = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
            
            resend.Emails.send({
                "from": from_address,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
                "html": html_content,
            })
            return True
        except Exception as e:
            raise Exception(f"Email send failed: {e}")
```

### Service Factories (`app/services/email/factory.py`)

```python
from functools import lru_cache
from app.core.config import settings
from app.services.email.base import BaseEmailService


class ConsoleEmailService(BaseEmailService):
    """Debug email service that prints to console."""
    
    async def send(self, to, subject, template, data, **kwargs):
        print(f"[EMAIL] To: {to}, Subject: {subject}, Template: {template}")
        return True
    
    async def send_raw(self, to, subject, html_content, **kwargs):
        print(f"[EMAIL] To: {to}, Subject: {subject}")
        return True


@lru_cache(maxsize=1)
def get_email_service() -> BaseEmailService:
    """Factory that returns configured email service."""
    
    if settings.EMAIL_PROVIDER == "resend":
        from app.services.email.resend import ResendEmailService
        return ResendEmailService()
    
    elif settings.EMAIL_PROVIDER == "sendgrid":
        from app.services.email.sendgrid import SendGridEmailService
        return SendGridEmailService()
    
    else:
        # Default: console (for development)
        return ConsoleEmailService()
```

---

## 10. API Design Patterns

### Router Aggregation (`app/api/v1/router.py`)

```python
from fastapi import APIRouter

from app.api.v1.public import health, webhooks, contact
from app.api.v1.app import users, projects, ai
from app.api.v1.admin import users as admin_users, jobs, metrics

# Public routes (no auth)
public_router = APIRouter(prefix="/public", tags=["Public"])
public_router.include_router(health.router)
public_router.include_router(webhooks.router, prefix="/webhooks")
public_router.include_router(contact.router, prefix="/contact")

# App routes (auth required)
app_router = APIRouter(prefix="/app", tags=["App"])
app_router.include_router(users.router, prefix="/users")
app_router.include_router(projects.router, prefix="/projects")
app_router.include_router(ai.router, prefix="/ai")

# Admin routes (auth + admin role required)
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
admin_router.include_router(admin_users.router, prefix="/users")
admin_router.include_router(jobs.router, prefix="/jobs")
admin_router.include_router(metrics.router, prefix="/metrics")

# Aggregate all v1 routes
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(public_router)
api_router.include_router(app_router)
api_router.include_router(admin_router)
```

### Dependency Injection (`app/api/deps.py`)

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import verify_token, get_current_user_id, require_admin
from app.models.user import User


# Database session dependency
DBSession = Annotated[AsyncSession, Depends(get_session)]

# Auth dependencies
TokenPayload = Annotated[dict, Depends(verify_token)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]


async def get_current_user(
    session: DBSession,
    user_id: CurrentUserId,
) -> User:
    """Get full user object from database."""
    from sqlmodel import select
    
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Auto-create user on first request (synced from auth provider)
        from app.business.user_service import create_user_from_token
        user = await create_user_from_token(session, user_id)
    
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
```

### Example CRUD Endpoint (`app/api/v1/app/projects.py`)

```python
from fastapi import APIRouter, HTTPException, status
from typing import List

from app.api.deps import DBSession, CurrentUser
from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectRead
from app.business.crud_base import CRUDBase

router = APIRouter()
project_crud = CRUDBase[Project, ProjectCreate, ProjectUpdate](Project)


@router.get("", response_model=List[ProjectRead])
async def list_projects(
    session: DBSession,
    user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
):
    """List user's projects."""
    from sqlmodel import select
    
    result = await session.execute(
        select(Project)
        .where(Project.owner_id == user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    session: DBSession,
    user: CurrentUser,
    project_in: ProjectCreate,
):
    """Create new project."""
    project = Project(
        **project_in.model_dump(),
        owner_id=user.id,
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    session: DBSession,
    user: CurrentUser,
    project_id: str,
):
    """Get project by ID."""
    project = await project_crud.get(session, id=project_id)
    
    if not project or project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    session: DBSession,
    user: CurrentUser,
    project_id: str,
    project_in: ProjectUpdate,
):
    """Update project."""
    project = await project_crud.get(session, id=project_id)
    
    if not project or project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return await project_crud.update(session, db_obj=project, obj_in=project_in)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    session: DBSession,
    user: CurrentUser,
    project_id: str,
):
    """Delete project."""
    project = await project_crud.get(session, id=project_id)
    
    if not project or project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    await project_crud.delete(session, id=project_id)
```

---

## 11. Error Handling

### Custom Exceptions (`app/core/exceptions.py`)

```python
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppException):
    """Resource not found."""
    def __init__(self, resource: str, id: str):
        super().__init__(
            message=f"{resource} not found",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": id}
        )


class ValidationError(AppException):
    """Input validation failed."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field} if field else {}
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int):
        super().__init__(
            message="Rate limit exceeded",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after}
        )


class ExternalServiceError(AppException):
    """External service (AI, email, etc.) failed."""
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} service error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service}
        )


async def app_exception_handler(request: Request, exc: AppException):
    """Global exception handler for AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )
```

---

## 12. Testing Strategy

### Test Configuration (`tests/conftest.py`)

```python
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from app.main import app
from app.core.db import get_session
from app.core.config import settings


# Test database URL (SQLite for speed, Postgres for accuracy)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture
async def session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide test database session."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    """Provide test HTTP client."""
    
    async def override_get_session():
        yield session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Mock auth headers for protected routes."""
    # In tests, you can mock the verify_token dependency
    # or generate real test tokens
    return {"Authorization": "Bearer test-token"}
```

### Example Test (`tests/unit/test_projects.py`)

```python
import pytest
from httpx import AsyncClient


class TestProjectEndpoints:
    """Test project CRUD endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/app/projects",
            json={"name": "Test Project", "description": "A test"},
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers):
        response = await client.get(
            "/api/v1/app/projects",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

---

## 13. Deployment

### Dockerfile (`docker/Dockerfile`)

```dockerfile
# Stage 1: Build
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -e .

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Create non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose (`docker/docker-compose.yml`)

```yaml
version: "3.9"

services:
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ../app:/app/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/omnistack
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: omnistack
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/omnistack
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    command: arq app.jobs.worker.WorkerSettings

volumes:
  postgres_data:
  redis_data:
```

### Railway Config (`railway.toml`)

```toml
[build]
builder = "dockerfile"
dockerfilePath = "docker/Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Makefile

```makefile
.PHONY: help dev up down migrate test lint seed shell

help:
	@echo "Available commands:"
	@echo "  make dev      - Start API with hot reload"
	@echo "  make up       - Start Docker services"
	@echo "  make down     - Stop Docker services"
	@echo "  make migrate  - Run database migrations"
	@echo "  make test     - Run test suite"
	@echo "  make lint     - Run linters"
	@echo "  make seed     - Seed database"
	@echo "  make shell    - Open Python shell"

dev:
	uvicorn app.main:app --reload --port 8000

up:
	docker compose -f docker/docker-compose.yml up -d db redis

down:
	docker compose -f docker/docker-compose.yml down

migrate:
	alembic revision --autogenerate -m "$(msg)"
	alembic upgrade head

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/
	ruff format app/ tests/ --check

seed:
	python scripts/seed.py

shell:
	python -c "from app.main import app; import asyncio; asyncio.run(shell())"

worker:
	arq app.jobs.worker.WorkerSettings
```

---

## 14. Security Checklist

### Pre-Launch Security Audit

- [ ] All secrets in environment variables, not code
- [ ] `.env` files in `.gitignore`
- [ ] CORS whitelist configured (not `*`)
- [ ] Rate limiting enabled on all routes
- [ ] SQL injection prevented (using SQLModel/SQLAlchemy)
- [ ] JWT verification using JWKS (not hardcoded secrets)
- [ ] Input validation on all endpoints (Pydantic)
- [ ] Error messages don't leak internal details
- [ ] Health check endpoints don't expose sensitive info
- [ ] Webhook signatures verified
- [ ] File uploads restricted by type and size
- [ ] Admin routes require role verification
- [ ] Logging redacts PII (emails, tokens)
- [ ] Dependencies scanned for vulnerabilities
- [ ] HTTPS enforced in production

### Security Headers (via middleware)

```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

---

## Appendix A: Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | FastAPI | Async-first, auto-docs, type hints |
| ORM | SQLModel | SQLAlchemy + Pydantic in one |
| Migrations | Alembic | Industry standard, async support |
| Background Jobs | ARQ | Pure async, Redis-only, simple |
| Rate Limiting | Custom | Full control, Redis-backed |
| AI Gateway | Custom | Multi-provider support needed |
| Testing | Pytest | Async support, fixtures |
| Linting | Ruff | Fast, replaces multiple tools |

---

## Appendix B: API Reference

### Authentication Flow

```
1. User authenticates with frontend (Clerk/Supabase)
2. Frontend receives JWT access token
3. Frontend sends token in Authorization header
4. Backend verifies token via JWKS
5. Backend extracts user_id from 'sub' claim
6. Backend creates/fetches user from database
7. Protected route executes with CurrentUser dependency
```

### Response Format

All API responses follow this structure:

**Success:**
```json
{
  "id": "...",
  "name": "...",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Error:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Project not found",
    "details": {
      "resource": "Project",
      "id": "123"
    }
  }
}
```

**List (with pagination):**
```json
{
  "items": [...],
  "total": 100,
  "skip": 0,
  "limit": 20
}
```

---

*This Technical PRD is the implementation blueprint for OmniStack Backend Boilerplate.*
