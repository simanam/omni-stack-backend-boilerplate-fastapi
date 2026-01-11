"""
Project CRUD endpoints.

Provides full CRUD operations for projects with ownership checks.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.business.project_service import project_service
from app.core.exceptions import NotFoundError
from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(tags=["Projects"])


@router.get("", response_model=PaginatedResponse[ProjectRead])
async def list_projects(
    session: DBSession,
    user: CurrentUser,
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by project name"),
):
    """
    List current user's projects with pagination.

    Returns only active (non-deleted) projects owned by the authenticated user.
    Supports optional search by project name.
    """
    if search:
        projects = await project_service.search_by_name(
            session, owner_id=user.id, query=search, skip=skip, limit=limit
        )
        # For search, we don't have an efficient total count, so we estimate
        total = len(projects) + skip if len(projects) == limit else len(projects) + skip
    else:
        projects = await project_service.get_active_by_owner(
            session, owner_id=user.id, skip=skip, limit=limit
        )
        total = await project_service.count_active_by_owner(session, owner_id=user.id)

    return PaginatedResponse(
        items=projects,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    session: DBSession,
    user: CurrentUser,
    project_in: ProjectCreate,
):
    """
    Create a new project.

    The project will be owned by the authenticated user.
    """
    project = await project_service.create_with_owner(
        session, obj_in=project_in, owner_id=user.id
    )
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    session: DBSession,
    user: CurrentUser,
    project_id: str,
):
    """
    Get a project by ID.

    Returns 404 if the project doesn't exist or doesn't belong to the user.
    """
    project = await project_service.get(session, id=project_id)

    if not project or project.owner_id != user.id or project.deleted_at is not None:
        raise NotFoundError("Project", project_id)

    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    session: DBSession,
    user: CurrentUser,
    project_id: str,
    project_in: ProjectUpdate,
):
    """
    Update a project.

    Only the project owner can update it.
    Returns 404 if the project doesn't exist or doesn't belong to the user.
    """
    project = await project_service.get(session, id=project_id)

    if not project or project.owner_id != user.id or project.deleted_at is not None:
        raise NotFoundError("Project", project_id)

    return await project_service.update(session, db_obj=project, obj_in=project_in)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    session: DBSession,
    user: CurrentUser,
    project_id: str,
):
    """
    Delete a project (soft delete).

    Only the project owner can delete it.
    The project is soft-deleted (marked with deleted_at timestamp).
    Returns 404 if the project doesn't exist or doesn't belong to the user.
    """
    project = await project_service.get(session, id=project_id)

    if not project or project.owner_id != user.id or project.deleted_at is not None:
        raise NotFoundError("Project", project_id)

    await project_service.soft_delete(session, id=project_id)
