"""Add mobile IAP fields to users table.

Revision ID: 20260110_220000
Revises: 20260110_210000
Create Date: 2026-01-10 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260110_220000"
down_revision: str | None = "20260110_210000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add Apple App Store field
    op.add_column(
        "users",
        sa.Column("apple_original_transaction_id", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_users_apple_original_transaction_id"),
        "users",
        ["apple_original_transaction_id"],
        unique=False,
    )

    # Add Google Play Store field
    op.add_column(
        "users",
        sa.Column("google_purchase_token", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_users_google_purchase_token"),
        "users",
        ["google_purchase_token"],
        unique=False,
    )


def downgrade() -> None:
    # Drop Google Play Store field
    op.drop_index(op.f("ix_users_google_purchase_token"), table_name="users")
    op.drop_column("users", "google_purchase_token")

    # Drop Apple App Store field
    op.drop_index(op.f("ix_users_apple_original_transaction_id"), table_name="users")
    op.drop_column("users", "apple_original_transaction_id")
