async def test_get_document(client):
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
                b"%PDF-1.4 fake pdf contents",
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    response = await client.get(
        f"/documents/{document_id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == document_id
    assert data["project_id"] == project_id
    assert data["original_filename"] == "guide.pdf"

async def test_upload_document(
    client,
    fake_storage,
):
    project_response = await client.post(
        "/projects",
        json={
            "name": "AWS Knowledge Base",
        },
    )

    project_id = project_response.json()["id"]

    response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "aws-guide.pdf",
                b"%PDF-1.4 fake pdf contents",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["original_filename"] == "aws-guide.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["file_size"] > 0
    assert data["status"] == "uploaded"

    assert len(fake_storage.files) == 1
    
async def test_upload_document_rejects_empty_file(client):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 400

async def test_upload_document_rejects_non_pdf(client):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "notes.txt",
                b"hello",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 415

async def test_user_cannot_upload_to_another_users_project(
    client,
    auth_user,
):
    auth_user["user_id"] = "user_A"

    project_response = await client.post(
        "/projects",
        json={"name": "Private Project"},
    )

    project_id = project_response.json()["id"]

    auth_user["user_id"] = "user_B"

    response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "private.pdf",
                b"%PDF-1.4 fake",
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 404

async def test_get_document_download_url(
    client,
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
                b"%PDF-1.4 fake pdf contents",
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    response = await client.get(
        f"/documents/{document_id}/download"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["expires_in"] == 300
    assert data["url"].startswith(
        "https://fake-storage.local/"
    )