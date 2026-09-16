import asyncio
from uuid import UUID

from app.worker.tasks import process_ingestion_job_task


class CeleryTaskQueue:
    async def enqueue_ingestion(
        self,
        *,
        job_id: UUID,
    ) -> str:
        result = await asyncio.to_thread(
            process_ingestion_job_task.delay,
            str(job_id),
        )

        return result.id