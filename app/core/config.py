"""
Application configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    API_V2_STR: str = "/api/v2"
    BACKEND_CORS_ORIGINS: str = '["http://localhost:3000"]'

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v  # Keep as string, parse in computed_field

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
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
    REDIS_URL: str | None = None
    UPSTASH_REDIS_REST_URL: str | None = None
    UPSTASH_REDIS_REST_TOKEN: str | None = None

    @computed_field
    @property
    def redis_available(self) -> bool:
        return bool(self.REDIS_URL or self.UPSTASH_REDIS_REST_URL)

    # --- Authentication ---
    AUTH_PROVIDER: Literal["supabase", "clerk", "custom"] = "supabase"

    # Supabase
    SUPABASE_PROJECT_URL: str | None = None
    SUPABASE_JWT_SECRET: str | None = None  # Legacy HS256

    # Clerk
    CLERK_ISSUER_URL: str | None = None
    CLERK_SECRET_KEY: str | None = None

    # Custom OAuth
    OAUTH_JWKS_URL: str | None = None
    OAUTH_AUDIENCE: str | None = None
    OAUTH_ISSUER: str | None = None

    @computed_field
    @property
    def jwks_url(self) -> str | None:
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
    AI_DEFAULT_PROVIDER: Literal["openai", "anthropic", "gemini"] = "openai"
    AI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None  # For Gemini
    PERPLEXITY_API_KEY: str | None = None

    @computed_field
    @property
    def ai_available(self) -> bool:
        return bool(self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY or self.GOOGLE_API_KEY)

    # --- Email ---
    EMAIL_PROVIDER: Literal["resend", "sendgrid", "console"] = "console"
    EMAIL_FROM_ADDRESS: str = "hello@example.com"
    EMAIL_FROM_NAME: str = "My App"
    ADMIN_EMAIL: str | None = None  # Admin notification email
    RESEND_API_KEY: str | None = None
    SENDGRID_API_KEY: str | None = None

    # --- Storage ---
    STORAGE_PROVIDER: Literal["s3", "r2", "cloudinary", "local"] = "local"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str | None = None
    R2_ACCOUNT_ID: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET: str | None = None
    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None

    # --- Stripe ---
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_ID_MONTHLY: str | None = None
    STRIPE_PRICE_ID_YEARLY: str | None = None

    @computed_field
    @property
    def stripe_available(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)

    # --- Apple App Store (In-App Purchases) ---
    APPLE_BUNDLE_ID: str | None = None  # e.g., "com.example.myapp"
    APPLE_SHARED_SECRET: str | None = None  # App-specific shared secret for receipt verification

    @computed_field
    @property
    def apple_iap_available(self) -> bool:
        return bool(self.APPLE_BUNDLE_ID)

    # --- Google Play Store (In-App Purchases) ---
    GOOGLE_PLAY_PACKAGE_NAME: str | None = None  # e.g., "com.example.myapp"
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: str | None = None  # Base64-encoded service account JSON

    @computed_field
    @property
    def google_iap_available(self) -> bool:
        return bool(self.GOOGLE_PLAY_PACKAGE_NAME and self.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON)

    # --- Observability ---
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # --- OpenTelemetry Tracing ---
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str | None = None  # Defaults to PROJECT_NAME
    OTEL_EXPORTER: Literal["otlp", "console", "zipkin", "none"] = "otlp"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None  # e.g., "http://localhost:4317"
    OTEL_EXPORTER_ZIPKIN_ENDPOINT: str | None = None  # e.g., "http://localhost:9411/api/v2/spans"
    OTEL_TRACES_SAMPLER_ARG: float = 1.0  # Sampling rate (0.0 to 1.0)

    # --- Rate Limiting ---
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AI: str = "10/minute"
    RATE_LIMIT_AUTH: str = "5/minute"

    # --- Contact Form ---
    CONTACT_REQUIRE_SUBJECT: bool = False  # Make subject optional by default
    CONTACT_REQUIRE_PHONE: bool = False
    CONTACT_SEND_CONFIRMATION: bool = True  # Send confirmation to sender
    CONTACT_WEBHOOK_URL: str | None = None  # Webhook for CRM/integrations
    CONTACT_RATE_LIMIT: str = "5/hour"  # Rate limit per IP

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra env vars
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


# Singleton instance for direct import
settings = get_settings()
