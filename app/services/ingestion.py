from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.models.ingestion_batch import IngestionBatch, IngestionBatchStatus
from app.models.ingestion_job import IngestionJob, IngestionJobStatus
from app.parsing.unstructured_parser import UnstructuredPdfParser
from app.services.document_processor import process_document
from app.storage.dependencies import get_storage

IngestionProcessor = Callable[
    [Document],
    Awaitable[None]
]

async def run_ingestion_job(
    job_id: UUID,
) -> None:
    async with AsyncSessionLocal() as db:
        async def processor(
            document: Document,
        ) -> None:
            
            storage = get_storage()
            
            parser = UnstructuredPdfParser(
                strategy="fast"
            )
            
            await process_document(
                document=document,
                storage=storage,
                parser=parser
            )
        
        async with AsyncSessionLocal() as db:
            await process_ingestion_job(
                db=db,
                job_id=job_id,
                processor=processor,
            )

async def update_ingestion_batch_status(
    db: AsyncSession,
    batch_id: UUID,
) -> None:
    batch_result = await db.execute(
        select(IngestionBatch)
        .where(
            IngestionBatch.id == batch_id
        )
        .with_for_update()
    )
    
    batch = batch_result.scalar_one_or_none()
    
    if batch is None:
        return

    result = await db.execute(
        select(
            IngestionJob.status,
            func.count(IngestionJob.id),
        )
        .where(
            IngestionJob.batch_id == batch_id
        )
        .group_by(
            IngestionJob.status
        )
    )
    
    rows = result.all()
    
    counts = {
        status: count
        for status, count in rows
    }
    
    queued = counts.get(
        IngestionJobStatus.QUEUED,
        0,
    )

    processing = counts.get(
        IngestionJobStatus.PROCESSING,
        0,
    )

    completed = counts.get(
        IngestionJobStatus.COMPLETED,
        0,
    )

    failed = counts.get(
        IngestionJobStatus.FAILED,
        0,
    )
    
    total = (
        queued
        + processing
        + completed
        + failed
    )
    
    if total == 0:
        return
    
    if completed == total:
        batch.status = (
            IngestionBatchStatus.COMPLETED
        )

    elif failed == total:
        batch.status = (
            IngestionBatchStatus.FAILED
        )

    elif completed + failed == total:
        batch.status = (
            IngestionBatchStatus.PARTIALLY_FAILED
        )

    elif (
        processing > 0
        or completed > 0
        or failed > 0
    ):
        batch.status = (
            IngestionBatchStatus.PROCESSING
        )

    else:
        batch.status = (
            IngestionBatchStatus.QUEUED
        )

async def process_ingestion_job(db: AsyncSession, job_id: UUID, processor: IngestionProcessor) -> None:
    result = await db.execute(
        select(IngestionJob).where(
            IngestionJob.id == job_id
        )
        .with_for_update()
    )
    
    job = result.scalar_one_or_none()
    
    if job is None:
        return
    
    if job.status != IngestionJobStatus.QUEUED:
        return
    
    document_result = await db.execute(
        select(Document).where(
            Document.id == job.document_id,
            Document.deleted_at.is_(None),
        )
    )
    
    document = document_result.scalar_one_or_none()
    
    if document is None:
        job.status = IngestionJobStatus.FAILED
        job.error_message = "Document not found"
        job.completed_at = datetime.now(timezone.utc)
        
        await db.flush()
        
        await update_ingestion_batch_status(
            db=db,
            batch_id=job.batch_id,
        )

        await db.commit()
        return
    
    job.status = IngestionJobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    job.attempt_count += 1
    job.error_message = None
    
    document.status = DocumentStatus.PROCESSING
    
    await db.flush()
    
    await update_ingestion_batch_status(
        db=db,
        batch_id=job.batch_id,
    )
    
    await db.commit()
    
    try:
        await processor(document)
        
        job.status = IngestionJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        
        document.status = DocumentStatus.READY
        
        await db.flush()

        await update_ingestion_batch_status(
            db=db,
            batch_id=job.batch_id,
        )
        
        await db.commit()
    
    except Exception as exc:
        await db.rollback()
        
        job_result = await db.execute(
            select(IngestionJob).where(
                IngestionJob.id == job_id
            )
        )
        
        job = job_result.scalar_one_or_none()
        
        if job is None:
            raise
        
        document_result = await db.execute(
            select(Document).where(
                Document.id == job.document_id
            )
        )
        
        document = document_result.scalar_one_or_none()
        
        job.status = IngestionJobStatus.FAILED
        job.error_message = str(exc)[:4000]
        job.completed_at = datetime.now(timezone.utc)
        
        if document is not None:
            document.status = DocumentStatus.FAILED
            
        await db.flush()
            
        await update_ingestion_batch_status(
            db=db,
            batch_id=job.batch_id,
        )
        
        await db.commit()
        
        raise