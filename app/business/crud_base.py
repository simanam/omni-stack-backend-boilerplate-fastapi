"""
Generic CRUD base class for SQLModel entities.

Provides reusable create, read, update, delete operations
that can be extended by specific service classes.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic CRUD operations for any SQLModel.

    Usage:
        class ProjectCRUD(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
            pass

        project_crud = ProjectCRUD(Project)
        project = await project_crud.get(session, id="123")
    """

    def __init__(self, model: type[ModelType]):
        """
        Initialize CRUD with the model class.

        Args:
            model: The SQLModel class to perform operations on.
        """
        self.model = model

    async def get(
        self,
        session: AsyncSession,
        id: str,
    ) -> ModelType | None:
        """
        Get a single record by ID.

        Args:
            session: Database session.
            id: The record's primary key.

        Returns:
            The model instance or None if not found.
        """
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_field(
        self,
        session: AsyncSession,
        field: str,
        value: Any,
    ) -> ModelType | None:
        """
        Get a single record by an arbitrary field.

        Args:
            session: Database session.
            field: The field name to query.
            value: The value to match.

        Returns:
            The model instance or None if not found.
        """
        result = await session.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Get multiple records with pagination.

        Args:
            session: Database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of model instances.
        """
        result = await session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_multi_by_owner(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Get multiple records by owner with pagination.

        Args:
            session: Database session.
            owner_id: The owner's ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of model instances.
        """
        result = await session.execute(
            select(self.model)
            .where(self.model.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(self, session: AsyncSession) -> int:
        """
        Get total count of records.

        Args:
            session: Database session.

        Returns:
            Total count.
        """
        result = await session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def count_by_owner(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
    ) -> int:
        """
        Get total count of records for a specific owner.

        Args:
            session: Database session.
            owner_id: The owner's ID.

        Returns:
            Total count.
        """
        result = await session.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.owner_id == owner_id)
        )
        return result.scalar_one()

    async def create(
        self,
        session: AsyncSession,
        *,
        obj_in: CreateSchemaType,
    ) -> ModelType:
        """
        Create a new record.

        Args:
            session: Database session.
            obj_in: Schema with data for the new record.

        Returns:
            The created model instance.
        """
        db_obj = self.model.model_validate(obj_in)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def create_with_owner(
        self,
        session: AsyncSession,
        *,
        obj_in: CreateSchemaType,
        owner_id: str,
    ) -> ModelType:
        """
        Create a new record with owner assignment.

        Args:
            session: Database session.
            obj_in: Schema with data for the new record.
            owner_id: The owner's ID.

        Returns:
            The created model instance.
        """
        obj_data = obj_in.model_dump()
        obj_data["owner_id"] = owner_id
        db_obj = self.model(**obj_data)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        session: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
    ) -> ModelType:
        """
        Update an existing record.

        Args:
            session: Database session.
            db_obj: The existing model instance.
            obj_in: Schema with update data.

        Returns:
            The updated model instance.
        """
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
        id: str,
    ) -> ModelType | None:
        """
        Hard delete a record.

        Args:
            session: Database session.
            id: The record's primary key.

        Returns:
            The deleted model instance or None if not found.
        """
        obj = await self.get(session, id=id)
        if obj:
            await session.delete(obj)
            await session.flush()
        return obj

    async def soft_delete(
        self,
        session: AsyncSession,
        *,
        id: str,
    ) -> ModelType | None:
        """
        Soft delete a record (requires SoftDeleteMixin).

        Sets deleted_at to current timestamp instead of removing the record.

        Args:
            session: Database session.
            id: The record's primary key.

        Returns:
            The soft-deleted model instance or None if not found.
        """
        obj = await self.get(session, id=id)
        if obj and hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.utcnow()
            session.add(obj)
            await session.flush()
            await session.refresh(obj)
        return obj

    async def restore(
        self,
        session: AsyncSession,
        *,
        id: str,
    ) -> ModelType | None:
        """
        Restore a soft-deleted record.

        Args:
            session: Database session.
            id: The record's primary key.

        Returns:
            The restored model instance or None if not found.
        """
        obj = await self.get(session, id=id)
        if obj and hasattr(obj, "deleted_at"):
            obj.deleted_at = None
            session.add(obj)
            await session.flush()
            await session.refresh(obj)
        return obj
