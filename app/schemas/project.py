"""
Project schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel


class ProjectBase(SQLModel):
    """Base schema with common project fields."""

    name: str = Field(min_length=1, max_length=255, description="Project name")
    description: str | None = Field(
        default=None, max_length=2000, description="Project description"
    )


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    pass


class ProjectUpdate(SQLModel):
    """Schema for updating a project (all fields optional)."""

    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="Project name"
    )
    description: str | None = Field(
        default=None, max_length=2000, description="Project description"
    )


class ProjectRead(ProjectBase):
    """Schema for API responses - project data."""

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class ProjectReadWithDeleted(ProjectRead):
    """Extended schema including soft delete timestamp."""

    deleted_at: datetime | None = None
