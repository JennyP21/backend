import asyncio
import sys
from uuid import UUID

from app.worker.celery_app import celery_app
from app.services.ingestion import process_ingestion_job


_worker_loop: asyncio.AbstractEventLoop | None = None


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop

    if _worker_loop is None or _worker_loop.is_closed():
        if sys.platform == "win32":
            _worker_loop = asyncio.SelectorEventLoop()
        else:
            _worker_loop = asyncio.new_event_loop()

        asyncio.set_event_loop(_worker_loop)

    return _worker_loop


@celery_app.task(
    name="raglab.process_ingestion_job",
)
def process_ingestion_job_task(
    job_id: str,
) -> None:
    loop = get_worker_event_loop()

    loop.run_until_complete(
        process_ingestion_job(
            UUID(job_id)
        )
    )