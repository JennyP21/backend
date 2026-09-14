from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_user
from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate,
    user_id: Annotated[str, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
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