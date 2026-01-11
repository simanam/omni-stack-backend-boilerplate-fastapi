"""
User model synced from auth provider.
The `id` field matches the `sub` claim from JWT tokens.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.file import File

# Type aliases for clarity
UserRole = Literal["user", "admin", "superadmin"]
SubscriptionStatus = Literal["active", "canceled", "past_due", "trialing", "incomplete"]
SubscriptionPlan = Literal["free", "pro", "enterprise"]


class User(BaseModel, table=True):
    """
    User model synced from auth provider.
    The `id` field should match the `sub` claim from JWT.
    """

    __tablename__ = "users"

    # Override id to use auth provider's ID (not auto-generated UUID)
    id: str = Field(primary_key=True, description="Auth provider user ID (sub claim)")

    # Core profile
    email: str = Field(unique=True, index=True)
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2048)

    # Role & permissions
    role: str = Field(default="user", description="user | admin | superadmin")
    is_active: bool = Field(default=True)

    # Stripe subscription fields
    stripe_customer_id: str | None = Field(default=None, index=True)
    subscription_status: str | None = Field(
        default=None, description="active | canceled | past_due | trialing | incomplete"
    )
    subscription_plan: str | None = Field(
        default=None, description="free | pro | enterprise"
    )

    # Apple App Store (In-App Purchases)
    apple_original_transaction_id: str | None = Field(
        default=None, index=True, description="Apple original transaction ID for subscription lookup"
    )

    # Google Play Store (In-App Purchases)
    google_purchase_token: str | None = Field(
        default=None, index=True, description="Google Play purchase token for subscription lookup"
    )

    # Metadata
    last_login_at: datetime | None = Field(default=None)
    login_count: int = Field(default=0)

    # Relationships
    files: list["File"] = Relationship(back_populates="owner")


class UserBase(SQLModel):
    """Base schema with common user fields."""

    email: str
    full_name: str | None = None
    avatar_url: str | None = None


class UserCreate(UserBase):
    """Schema for creating a user (typically from webhook or first auth)."""

    id: str


class UserUpdate(SQLModel):
    """Schema for updating user profile (all fields optional)."""

    full_name: str | None = None
    avatar_url: str | None = None


class UserAdminUpdate(SQLModel):
    """Schema for admin updating user (includes role/status)."""

    full_name: str | None = None
    avatar_url: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserRead(SQLModel):
    """Schema for API responses - safe user data."""

    id: str
    email: str
    full_name: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    subscription_plan: str | None
    subscription_status: str | None
    created_at: datetime


class UserReadAdmin(UserRead):
    """Extended schema for admin views."""

    stripe_customer_id: str | None
    apple_original_transaction_id: str | None
    google_purchase_token: str | None
    last_login_at: datetime | None
    login_count: int
    updated_at: datetime
