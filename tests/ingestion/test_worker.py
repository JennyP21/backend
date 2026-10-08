import pytest
from sqlalchemy import select

from app.models.document import Document, DocumentStatus
from app.models.ingestion_job import (
    IngestionJob,
    IngestionJobStatus,
)
from app.services.document_processor import process_document
from app.services.ingestion import process_ingestion_job


async def test_process_ingestion_job_success(
    client,
    db_session,
):
    project_response = await client.post(
        "/projects",
        json={
            "name": "Knowledge Base",
        },
    )

    project_id = project_response.json()["id"]

    upload_response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "guide.pdf",
                b"%PDF-1.4 fake",
                "application/pdf",
            ),
        },
    )

    document_id = upload_response.json()["id"]

    batch_response = await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    assert batch_response.status_code == 201

    job_result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id
        )
    )

    job = job_result.scalar_one()

    assert job.status == IngestionJobStatus.QUEUED

    async def successful_processor(document):
        return None

    await process_ingestion_job(
        db=db_session,
        job_id=job.id,
        processor=successful_processor,
    )

    await db_session.refresh(job)

    document_result = await db_session.execute(
        select(Document).where(
            Document.id == document_id
        )
    )

    document = document_result.scalar_one()

    assert job.status == IngestionJobStatus.COMPLETED
    assert job.attempt_count == 1
    assert job.started_at is not None
    assert job.completed_at is not None
    assert job.error_message is None

    assert document.status == DocumentStatus.READY

async def test_process_ingestion_job_failure(
    client,
    db_session,
):
    project_response = await client.post(
        "/projects",
        json={
            "name": "Knowledge Base",
        },
    )

    project_id = project_response.json()["id"]

    upload_response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "broken.pdf",
                b"%PDF-1.4 broken",
                "application/pdf",
            ),
        },
    )

    document_id = upload_response.json()["id"]

    await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    job_result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id
        )
    )

    job = job_result.scalar_one()

    async def failing_processor(document):
        raise RuntimeError(
            "PDF parsing failed"
        )

    with pytest.raises(
        RuntimeError,
        match="PDF parsing failed",
    ):
        await process_ingestion_job(
            db=db_session,
            job_id=job.id,
            processor=failing_processor,
        )

    job_result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.id == job.id
        )
    )

    failed_job = job_result.scalar_one()

    document_result = await db_session.execute(
        select(Document).where(
            Document.id == document_id
        )
    )

    document = document_result.scalar_one()

    assert failed_job.status == IngestionJobStatus.FAILED
    assert failed_job.attempt_count == 1
    assert failed_job.started_at is not None
    assert failed_job.completed_at is not None
    assert failed_job.error_message == "PDF parsing failed"

    assert document.status == DocumentStatus.FAILED

async def test_completed_job_is_not_processed_again(
    client,
    db_session,
):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    upload_response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "guide.pdf",
                b"%PDF-1.4 content",
                "application/pdf",
            ),
        },
    )

    document_id = upload_response.json()["id"]

    await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id
        )
    )

    job = result.scalar_one()

    call_count = 0

    async def processor(document):
        nonlocal call_count
        call_count += 1

    await process_ingestion_job(
        db=db_session,
        job_id=job.id,
        processor=processor,
    )

    await process_ingestion_job(
        db=db_session,
        job_id=job.id,
        processor=processor,
    )

    assert call_count == 1

async def test_ingestion_job_fails_when_storage_download_fails(
    client,
    db_session,
    fake_storage,
):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    upload_response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "guide.pdf",
                b"%PDF-1.4 content",
                "application/pdf",
            ),
        },
    )

    document_id = upload_response.json()["id"]

    await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id
        )
    )

    job = result.scalar_one()

    document_result = await db_session.execute(
        select(Document).where(
            Document.id == document_id
        )
    )

    document = document_result.scalar_one()

    # Simulate the S3 object disappearing.
    fake_storage.files.clear()

    async def processor(document):
        await process_document(
            document=document,
            storage=fake_storage,
        )

    with pytest.raises(KeyError):
        await process_ingestion_job(
            db=db_session,
            job_id=job.id,
            processor=processor,
        )

    await db_session.refresh(job)
    await db_session.refresh(document)

    assert job.status == IngestionJobStatus.FAILED
    assert document.status == DocumentStatus.FAILED
    assert job.error_message is not None