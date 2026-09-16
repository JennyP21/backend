from sqlalchemy import select

from app.models.document import Document, DocumentStatus
from app.models.ingestion_job import IngestionJob, IngestionJobStatus


async def test_create_ingestion_batch_queues_uploaded_documents(
    client,
    db_session,
):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    first_upload = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "first.pdf",
                b"%PDF-1.4 first",
                "application/pdf",
            )
        },
    )

    second_upload = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "second.pdf",
                b"%PDF-1.4 second",
                "application/pdf",
            )
        },
    )

    first_id = first_upload.json()["id"]
    second_id = second_upload.json()["id"]

    response = await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    assert response.status_code == 201

    data = response.json()

    assert data["project_id"] == project_id
    assert data["status"] == "queued"
    assert data["queued_documents"] == 2

    jobs_result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.document_id.in_(
                [first_id, second_id]
            )
        )
    )

    jobs = jobs_result.scalars().all()

    assert len(jobs) == 2

    for job in jobs:
        assert job.status == IngestionJobStatus.QUEUED

    documents_result = await db_session.execute(
        select(Document).where(
            Document.id.in_(
                [first_id, second_id]
            )
        )
    )

    documents = documents_result.scalars().all()

    assert len(documents) == 2

    for document in documents:
        assert document.status == DocumentStatus.QUEUED
        
async def test_create_ingestion_batch_does_not_duplicate_jobs(
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
                b"%PDF-1.4 guide",
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    first_response = await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    assert second_response.status_code == 409

    result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id
        )
    )

    jobs = result.scalars().all()

    assert len(jobs) == 1