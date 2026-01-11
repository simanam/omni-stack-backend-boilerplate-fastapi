"""
File model for tracking uploaded files.
"""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class File(BaseModel, table=True):
    """File metadata stored in the database."""

    __tablename__ = "files"

    owner_id: str = Field(foreign_key="users.id", index=True)
    key: str = Field(index=True)
    filename: str
    content_type: str | None = None
    size: int = 0
    status: str = Field(default="pending")

    owner: "User" = Relationship(back_populates="files")
