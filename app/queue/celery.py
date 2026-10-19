import asyncio
from uuid import UUID

from app.worker.celery_app import celery_app


class CeleryTaskQueue:
    async def enqueue_ingestion(
        self,
        *,
        job_id: UUID,
    ) -> str:
        result = await asyncio.to_thread(
            celery_app.send_task,
            "raglab.process_ingestion_job",
            args=[str(job_id)],
        )

        return result.id