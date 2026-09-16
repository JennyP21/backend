from sqlalchemy import select

from app.models.ingestion_job import IngestionJob


async def test_upload_does_not_create_ingestion_job(
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
                b"%PDF-1.4 fake contents",
                "application/pdf",
            ),
        },
    )

    assert upload_response.status_code == 201

    data = upload_response.json()

    assert data["status"] == "uploaded"

    document_id = data["id"]

    result = await db_session.execute(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id
        )
    )

    job = result.scalar_one_or_none()

    assert job is None
