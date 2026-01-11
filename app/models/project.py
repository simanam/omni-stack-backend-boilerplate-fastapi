"""
Project model - example resource with ownership.

Demonstrates CRUD patterns with soft delete support.
"""

from sqlmodel import Field

from app.models.base import BaseModel, SoftDeleteMixin


class Project(BaseModel, SoftDeleteMixin, table=True):
    """
    Project model with owner relationship.

    Extends BaseModel for id, created_at, updated_at.
    Extends SoftDeleteMixin for soft delete support.
    """

    __tablename__ = "projects"

    # Core fields
    name: str = Field(max_length=255, index=True, description="Project name")
    description: str | None = Field(
        default=None, max_length=2000, description="Project description"
    )

    # Ownership
    owner_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="User ID who owns this project",
    )

    # Optional: if you want to load the owner relationship
    # owner: "User" = Relationship(back_populates="projects")
