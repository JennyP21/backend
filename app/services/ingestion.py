from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.models.ingestion_job import IngestionJob, IngestionJobStatus


async def process_ingestion_job(job_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(IngestionJob).where(
                IngestionJob.id == job_id
            )
        )
        
        job = result.scalar_one_or_none()
        
        if job is None:
            return
        
        if job.status != IngestionJobStatus.QUEUED:
            return
        
        job.status = IngestionJobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        job.attempt_count += 1
        
        document_result = await db.execute(
            select(Document).where(
                Document.id == job.document_id
            )
        )
        
        document = document_result.scalar_one()
        
        document.status = DocumentStatus.PROCESSING
        
        await db.commit()