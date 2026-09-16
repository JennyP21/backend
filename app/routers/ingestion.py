from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from sqlalchemy import select

from app.dependencies import CurrentUserId, DbSession
from app.models.document import Document, DocumentStatus
from app.models.ingestion_batch import (
    IngestionBatch,
    IngestionBatchStatus,
)
from app.models.ingestion_job import (
    IngestionJob,
    IngestionJobStatus,
)
from app.schemas.ingestion import IngestionBatchResponse
from app.services.project import get_owned_project


router = APIRouter(
    tags=["Ingestion"],
)

@router.post(
    "/projects/{project_id}/ingestion-batches",
    response_model=IngestionBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ingestion_batch(
    project_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
):
    # Verify project ownership
    await get_owned_project(
        db=db,
        user_id=user_id,
        project_id=project_id,
    )

    # Find eligible documents and lock them
    result = await db.execute(
        select(Document)
        .where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
            Document.status == DocumentStatus.UPLOADED,
        )
        .with_for_update(
            skip_locked=True
        )
    )

    documents = result.scalars().all()

    if not documents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No uploaded documents are available for processing",
        )

    batch = IngestionBatch(
        project_id=project_id,
        created_by=user_id,
        status=IngestionBatchStatus.QUEUED,
    )

    db.add(batch)

    # We need the batch ID before creating jobs.
    await db.flush()

    for document in documents:
        document.status = DocumentStatus.QUEUED

        job = IngestionJob(
            batch_id=batch.id,
            document_id=document.id,
            status=IngestionJobStatus.QUEUED,
        )

        db.add(job)

    await db.commit()
    await db.refresh(batch)

    return IngestionBatchResponse(
        id=batch.id,
        project_id=batch.project_id,
        status=batch.status,
        queued_documents=len(documents),
        created_at=batch.created_at,
    )