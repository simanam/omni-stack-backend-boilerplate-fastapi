"""
Project business logic service.

Extends CRUDBase with project-specific operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.crud_base import CRUDBase
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """
    Project service with custom business logic.

    Inherits standard CRUD operations and adds project-specific methods.
    """

    def __init__(self):
        super().__init__(Project)

    async def get_active_by_owner(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """
        Get active (non-deleted) projects for an owner.

        Args:
            session: Database session.
            owner_id: The owner's ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of active projects.
        """
        result = await session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_active_by_owner(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
    ) -> int:
        """
        Count active (non-deleted) projects for an owner.

        Args:
            session: Database session.
            owner_id: The owner's ID.

        Returns:
            Count of active projects.
        """
        from sqlalchemy import func

        result = await session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.owner_id == owner_id)
            .where(Project.deleted_at.is_(None))
        )
        return result.scalar_one()

    async def get_by_name_and_owner(
        self,
        session: AsyncSession,
        *,
        name: str,
        owner_id: str,
    ) -> Project | None:
        """
        Get a project by name for a specific owner.

        Args:
            session: Database session.
            name: Project name.
            owner_id: The owner's ID.

        Returns:
            Project or None if not found.
        """
        result = await session.execute(
            select(Project)
            .where(Project.name == name)
            .where(Project.owner_id == owner_id)
            .where(Project.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def search_by_name(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """
        Search projects by name (case-insensitive).

        Args:
            session: Database session.
            owner_id: The owner's ID.
            query: Search query string.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of matching projects.
        """
        result = await session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .where(Project.deleted_at.is_(None))
            .where(Project.name.ilike(f"%{query}%"))
            .order_by(Project.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


# Singleton instance for convenience
project_service = ProjectService()
