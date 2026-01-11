"""add_contact_submission_model

Revision ID: 3f7a8b9c0d12
Revises: 9c4d6e8f0b23
Create Date: 2026-01-11 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3f7a8b9c0d12"
down_revision: Union[str, None] = "9c4d6e8f0b23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create contact_submissions table
    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        # Core fields
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        # Optional standard fields
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("company", sa.String(200), nullable=True),
        # Custom fields
        sa.Column(
            "extra_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        # Tracking
        sa.Column("reference_id", sa.String(20), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("replied_by", sa.String(), nullable=True),
        # Webhook tracking
        sa.Column("webhook_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("webhook_sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_contact_submissions_id", "contact_submissions", ["id"])
    op.create_index(
        "ix_contact_submissions_reference_id",
        "contact_submissions",
        ["reference_id"],
        unique=True,
    )
    op.create_index("ix_contact_submissions_email", "contact_submissions", ["email"])
    op.create_index("ix_contact_submissions_status", "contact_submissions", ["status"])
    op.create_index(
        "ix_contact_submissions_created_at", "contact_submissions", ["created_at"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_contact_submissions_created_at", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_status", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_email", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_reference_id", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_id", table_name="contact_submissions")
    # Drop table
    op.drop_table("contact_submissions")
