async def test_create_ingestion_batch_enqueues_jobs(
    client,
    fake_task_queue,
):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    for i in range(3):
        await client.post(
            f"/projects/{project_id}/documents",
            files={
                "file": (
                    f"document-{i}.pdf",
                    b"%PDF-1.4 contents",
                    "application/pdf",
                )
            },
        )

    response = await client.post(
        f"/projects/{project_id}/ingestion-batches"
    )

    assert response.status_code == 201

    assert len(fake_task_queue.job_ids) == 3