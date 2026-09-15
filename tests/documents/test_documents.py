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

async def test_list_project_documents(client):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "first.pdf",
                b"%PDF-1.4 first document",
                "application/pdf",
            )
        },
    )

    await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "second.pdf",
                b"%PDF-1.4 second document",
                "application/pdf",
            )
        },
    )

    response = await client.get(
        f"/projects/{project_id}/documents"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    filenames = {
        document["original_filename"]
        for document in data
    }

    assert filenames == {
        "first.pdf",
        "second.pdf",
    }

async def test_user_cannot_list_another_users_documents(
    client,
    auth_user,
):
    auth_user["user_id"] = "user_A"

    project_response = await client.post(
        "/projects",
        json={"name": "Private Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    auth_user["user_id"] = "user_B"

    response = await client.get(
        f"/projects/{project_id}/documents"
    )

    assert response.status_code == 404

async def test_list_documents_supports_pagination(client):
    project_response = await client.post(
        "/projects",
        json={"name": "Knowledge Base"},
    )

    project_id = project_response.json()["id"]

    for index in range(3):
        await client.post(
            f"/projects/{project_id}/documents",
            files={
                "file": (
                    f"document-{index}.pdf",
                    b"%PDF-1.4 content",
                    "application/pdf",
                )
            },
        )

    response = await client.get(
        f"/projects/{project_id}/documents",
        params={
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    
async def test_delete_document(
    client,
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
                b"%PDF-1.4 fake contents",
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    assert len(fake_storage.files) == 1

    response = await client.delete(
        f"/documents/{document_id}"
    )

    assert response.status_code == 204
    assert len(fake_storage.files) == 0

    get_response = await client.get(
        f"/documents/{document_id}"
    )

    assert get_response.status_code == 404

async def test_user_cannot_delete_another_users_document(
    client,
    auth_user,
):
    auth_user["user_id"] = "user_A"

    project_response = await client.post(
        "/projects",
        json={"name": "Private Project"},
    )

    project_id = project_response.json()["id"]

    upload_response = await client.post(
        f"/projects/{project_id}/documents",
        files={
            "file": (
                "private.pdf",
                b"%PDF-1.4 private",
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    auth_user["user_id"] = "user_B"

    response = await client.delete(
        f"/documents/{document_id}"
    )

    assert response.status_code == 404