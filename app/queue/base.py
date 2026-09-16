from typing import Protocol
from uuid import UUID


class TaskQueue(Protocol):
    async def enqueue_ingestion(
        self,
        *,
        job_id: UUID,
    ) -> str:
        ...