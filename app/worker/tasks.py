import asyncio
from uuid import UUID

from app.worker.celery_app import celery_app

@celery_app.task(
    name="raglab.process_ingestion_job",
)
def process_ingestion_job_task(job_id: str):
    from app.services.ingestion import process_ingestion_job
    
    asyncio.run(
        process_ingestion_job(
            UUID(job_id)
        )
    )