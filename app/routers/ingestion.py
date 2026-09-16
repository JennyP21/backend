from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from sqlalchemy import select, update

from app.dependencies import CurrentUserId, DbSession, Queue
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
    queue: Queue,
):
    # 1. Verify that the current user owns the project.
    await get_owned_project(
        db=db,
        user_id=user_id,
        project_id=project_id,
    )

    # 2. Find documents that are ready to be processed.
    #
    # FOR UPDATE prevents another concurrent request from selecting
    # the same documents.
    #
    # SKIP LOCKED means a second request won't wait for these rows;
    # it simply skips documents already claimed by another request.
    result = await db.execute(
        select(Document)
        .where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
            Document.status == DocumentStatus.UPLOADED,
        )
        .with_for_update(skip_locked=True)
    )

    documents = result.scalars().all()

    if not documents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No uploaded documents are available for processing",
        )

    # 3. Create one batch representing this Process Documents action.
    batch = IngestionBatch(
        project_id=project_id,
        created_by=user_id,
        status=IngestionBatchStatus.QUEUED,
    )

    db.add(batch)

    # Flush so batch.id is generated without committing the transaction.
    await db.flush()

    jobs: list[IngestionJob] = []

    # 4. Create one ingestion job per document and mark each
    # document as queued.
    for document in documents:
        document.status = DocumentStatus.QUEUED

        job = IngestionJob(
            batch_id=batch.id,
            document_id=document.id,
            status=IngestionJobStatus.QUEUED,
            attempt_count=0,
        )

        db.add(job)
        jobs.append(job)

    # Flush again so every job receives its UUID.
    await db.flush()

    # Capture primitive values before commit.
    batch_id = batch.id
    batch_created_at = batch.created_at
    job_ids = [job.id for job in jobs]

    # 5. Commit durable DB state BEFORE workers are allowed to run.
    #
    # At this point PostgreSQL permanently contains:
    #
    # - the batch
    # - all ingestion jobs
    # - all document status changes
    await db.commit()

    # 6. Dispatch jobs to Celery only after the DB commit.
    #
    # Workers can now safely look up these job IDs.
    for job_id in job_ids:
        celery_task_id = await queue.enqueue_ingestion(
            job_id=job_id,
        )

        # Store Celery's task ID on our own job record.
        await db.execute(
            update(IngestionJob)
            .where(
                IngestionJob.id == job_id
            )
            .values(
                celery_task_id=celery_task_id
            )
        )

    await db.commit()

    # 7. Return the batch to the frontend.
    return IngestionBatchResponse(
        id=batch_id,
        project_id=project_id,
        status=IngestionBatchStatus.QUEUED,
        queued_documents=len(documents),
        created_at=batch_created_at,
    )