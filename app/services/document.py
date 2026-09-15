from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.project import Project


async def get_owned_document(
    db: AsyncSession,
    user_id: str,
    document_id: UUID,
) -> Document:
    result = await db.execute(
        select(Document)
        .join(
            Project,
            Document.project_id == Project.id,
        )
        .where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
            Project.owner_id == user_id,
            Project.deleted_at.is_(None),
        )
    )

    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document