from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUserId, DbSession
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

async def get_owned_project(
    db: AsyncSession,
    user_id: str,
    project_id: UUID,
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == user_id,
            Project.deleted_at.is_(None),
        )
    )
    
    project = result.scalar_one_or_none()
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    return project

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate,
    user_id: CurrentUserId,
    db: DbSession,
):
    project = Project(
        owner_id=user_id,
        name=data.name,
        description=data.description,
    )

    db.add(project)

    await db.commit()
    await db.refresh(project)

    return project

@router.get(
    "",
    response_model=list[ProjectResponse],
)
async def get_projects(
    user_id: CurrentUserId,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    result = await db.execute(
        select(Project)
        .where(
            Project.owner_id == user_id,
            Project.deleted_at.is_(None),
        )
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return result.scalars().all()

@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def get_project(
    project_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
):
    return await get_owned_project(
        db=db,
        user_id=user_id,
        project_id=project_id,
    )

@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    user_id: CurrentUserId,
    db: DbSession,
):
    project = await get_owned_project(
        db=db,
        user_id=user_id,
        project_id=project_id,
    )

    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
):
    project = await get_owned_project(
        db=db,
        user_id=user_id,
        project_id=project_id,
    )

    project.deleted_at = datetime.now(timezone.utc)

    await db.commit()