from uuid import UUID
import uuid


async def test_create_project(client):
    response = await client.post(
        "/projects",
        json={
            "name": "AWS Knowledge Base",
            "description": "AWS documentation",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "AWS Knowledge Base"
    assert data["description"] == "AWS documentation"

    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    project_id = UUID(data["id"])

    assert str(project_id) == data["id"]


async def test_create_project_name_too_short(client):
    response = await client.post(
        "/projects",
        json={
            "name": "A",
        },
    )

    assert response.status_code == 422


async def test_get_projects(client):
    await client.post(
        "/projects",
        json={
            "name": "Project One",
            "description": "First project",
        },
    )

    await client.post(
        "/projects",
        json={
            "name": "Project Two",
            "description": "Second project",
        },
    )

    response = await client.get("/projects")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    names = {project["name"] for project in data}

    assert names == {
        "Project One",
        "Project Two",
    }


async def test_get_projects_only_returns_current_users_projects(
    client,
    auth_user,
):
    auth_user["user_id"] = "user_A"

    await client.post(
        "/projects",
        json={
            "name": "User A Project",
        },
    )

    auth_user["user_id"] = "user_B"

    await client.post(
        "/projects",
        json={
            "name": "User B Project",
        },
    )

    response = await client.get("/projects")

    assert response.status_code == 200

    projects = response.json()

    assert len(projects) == 1
    assert projects[0]["name"] == "User B Project"


async def test_get_projects_supports_pagination(client):
    for i in range(5):
        await client.post(
            "/projects",
            json={
                "name": f"Project {i}",
            },
        )

    response = await client.get(
        "/projects?limit=2&offset=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2


async def test_get_project(client):
    create_response = await client.post(
        "/projects",
        json={
            "name": "AWS Knowledge Base",
            "description": "AWS docs",
        },
    )

    project_id = create_response.json()["id"]

    response = await client.get(
        f"/projects/{project_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == project_id
    assert data["name"] == "AWS Knowledge Base"
    assert data["description"] == "AWS docs"


async def test_get_project_not_found(client):
    project_id = uuid.uuid4()

    response = await client.get(
        f"/projects/{project_id}"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Project not found",
    }


async def test_user_cannot_access_another_users_project(
    client,
    auth_user,
):
    auth_user["user_id"] = "user_A"

    create_response = await client.post(
        "/projects",
        json={
            "name": "User A Private Project",
        },
    )

    project_id = create_response.json()["id"]

    auth_user["user_id"] = "user_B"

    response = await client.get(
        f"/projects/{project_id}"
    )

    assert response.status_code == 404


async def test_update_project(client):
    create_response = await client.post(
        "/projects",
        json={
            "name": "Old Name",
            "description": "Old description",
        },
    )

    project_id = create_response.json()["id"]

    response = await client.patch(
        f"/projects/{project_id}",
        json={
            "name": "New Name",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "New Name"

    # Description should remain unchanged because it was not
    # included in the PATCH request.
    assert data["description"] == "Old description"


async def test_update_project_can_clear_description(client):
    create_response = await client.post(
        "/projects",
        json={
            "name": "My Project",
            "description": "Remove me",
        },
    )

    project_id = create_response.json()["id"]

    response = await client.patch(
        f"/projects/{project_id}",
        json={
            "description": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


async def test_update_project_not_found(client):
    project_id = uuid.uuid4()

    response = await client.patch(
        f"/projects/{project_id}",
        json={
            "name": "New Name",
        },
    )

    assert response.status_code == 404


async def test_user_cannot_update_another_users_project(
    client,
    auth_user,
):
    auth_user["user_id"] = "user_A"

    create_response = await client.post(
        "/projects",
        json={
            "name": "Private Project",
            "description": "Owned by A",
        },
    )

    project_id = create_response.json()["id"]

    auth_user["user_id"] = "user_B"

    response = await client.patch(
        f"/projects/{project_id}",
        json={
            "name": "Changed by B",
        },
    )

    assert response.status_code == 404


async def test_delete_project(client):
    create_response = await client.post(
        "/projects",
        json={
            "name": "Delete Me",
        },
    )

    project_id = create_response.json()["id"]

    response = await client.delete(
        f"/projects/{project_id}"
    )

    assert response.status_code == 204

    get_response = await client.get(
        f"/projects/{project_id}"
    )

    assert get_response.status_code == 404


async def test_delete_project_not_found(client):
    project_id = uuid.uuid4()

    response = await client.delete(
        f"/projects/{project_id}"
    )

    assert response.status_code == 404


async def test_user_cannot_delete_another_users_project(
    client,
    auth_user,
):
    auth_user["user_id"] = "user_A"

    create_response = await client.post(
        "/projects",
        json={
            "name": "Private Project",
        },
    )

    project_id = create_response.json()["id"]

    auth_user["user_id"] = "user_B"

    response = await client.delete(
        f"/projects/{project_id}"
    )

    assert response.status_code == 404


async def test_deleted_project_not_returned_in_list(client):
    create_response = await client.post(
        "/projects",
        json={
            "name": "Temporary Project",
        },
    )

    project_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/projects/{project_id}"
    )

    assert delete_response.status_code == 204

    response = await client.get("/projects")

    assert response.status_code == 200

    ids = [
        project["id"]
        for project in response.json()
    ]

    assert project_id not in ids