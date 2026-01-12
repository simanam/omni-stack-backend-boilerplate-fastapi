"""
Database compatibility utilities for SQLite fallback.

Provides cross-database compatible column types for PostgreSQL and SQLite.
Phase 12.8: SQLite Fallback

Usage:
    from app.models.compat import JSONColumn, ArrayColumn

    class MyModel(BaseModel, table=True):
        data: dict = Field(sa_column=JSONColumn())
        tags: list[str] = Field(sa_column=ArrayColumn(String))
"""

import json
from typing import Any

from sqlalchemy import JSON, Column, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.core.config import settings


def JSONColumn(nullable: bool = False, default: Any = None) -> Column:
    """
    Create a JSON column compatible with both PostgreSQL (JSONB) and SQLite (JSON).

    Args:
        nullable: Whether the column can be NULL
        default: Default value (should be a callable like dict or list for mutable defaults)

    Returns:
        SQLAlchemy Column with appropriate type for current database
    """
    if settings.is_sqlite:
        return Column(JSON, nullable=nullable, default=default or {})
    return Column(JSONB, nullable=nullable, default=default or {})


def ArrayColumn(item_type: type = String, nullable: bool = False, default: Any = None) -> Column:
    """
    Create an array column compatible with both PostgreSQL (ARRAY) and SQLite (JSON).

    SQLite doesn't support native arrays, so we store as JSON.

    Args:
        item_type: Type of array elements (only used for PostgreSQL)
        nullable: Whether the column can be NULL
        default: Default value (should be [] for empty list)

    Returns:
        SQLAlchemy Column with appropriate type for current database
    """
    if settings.is_sqlite:
        return Column(JSON, nullable=nullable, default=default or [])
    return Column(ARRAY(item_type), nullable=nullable, default=default or [])


class JSONEncodedList(TypeDecorator):
    """
    A TypeDecorator that stores Python lists as JSON strings.
    Useful for SQLite compatibility when you need list storage.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: list | None, dialect: Any) -> str | None:  # noqa: ARG002
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: str | None, dialect: Any) -> list | None:  # noqa: ARG002
        if value is None:
            return None
        return json.loads(value)


class JSONEncodedDict(TypeDecorator):
    """
    A TypeDecorator that stores Python dicts as JSON strings.
    Useful for SQLite compatibility when you need dict storage.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: dict | None, dialect: Any) -> str | None:  # noqa: ARG002
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: str | None, dialect: Any) -> dict | None:  # noqa: ARG002
        if value is None:
            return None
        return json.loads(value)


def get_json_type() -> type:
    """Get the appropriate JSON type for current database."""
    if settings.is_sqlite:
        return JSON
    return JSONB


def get_array_type(item_type: type = String) -> type:
    """Get the appropriate array type for current database."""
    if settings.is_sqlite:
        return JSON  # SQLite uses JSON for array storage
    return ARRAY(item_type)
