import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_project(client: AsyncClient, auth_headers: dict, name: str = "Demo Project") -> str:
    response = await client.post("/api/projects", json={"name": name}, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_and_get_task(client: AsyncClient, auth_headers: dict):
    project_id = await _create_project(client, auth_headers)

    create_response = await client.post(
        "/api/tasks",
        json={"title": "Write README", "project_id": project_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    task = create_response.json()
    assert task["title"] == "Write README"
    assert task["status"] == "TODO"
    assert task["project_id"] == project_id

    get_response = await client.get(f"/api/tasks/{task['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["project_id"] == project_id


async def test_create_task_for_missing_project_returns_404(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/tasks",
        json={"title": "Orphan task", "project_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_list_tasks_filtered_by_project_and_status(client: AsyncClient, auth_headers: dict):
    project_id = await _create_project(client, auth_headers)
    other_project_id = await _create_project(client, auth_headers, name="Other Project")

    t1 = await client.post(
        "/api/tasks",
        json={"title": "Task 1", "project_id": project_id},
        headers=auth_headers,
    )
    await client.post(
        "/api/tasks",
        json={"title": "Task 2", "project_id": other_project_id},
        headers=auth_headers,
    )

    response = await client.get("/api/tasks", params={"projectId": project_id})
    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert titles == ["Task 1"]

    task_id = t1.json()["id"]
    await client.patch(
        f"/api/tasks/{task_id}/status", json={"status": "DONE"}, headers=auth_headers
    )
    response = await client.get("/api/tasks", params={"status": "DONE"})
    assert response.status_code == 200
    assert any(t["id"] == task_id for t in response.json())


async def test_update_task_status(client: AsyncClient, auth_headers: dict):
    project_id = await _create_project(client, auth_headers)
    create_response = await client.post(
        "/api/tasks", json={"title": "Move me", "project_id": project_id}, headers=auth_headers
    )
    task_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"


async def test_delete_task(client: AsyncClient, auth_headers: dict):
    project_id = await _create_project(client, auth_headers)
    create_response = await client.post(
        "/api/tasks", json={"title": "Delete me", "project_id": project_id}, headers=auth_headers
    )
    task_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/tasks/{task_id}")
    assert get_response.status_code == 404


async def test_get_unknown_task_returns_404(client: AsyncClient):
    response = await client.get(f"/api/tasks/{uuid.uuid4()}")
    assert response.status_code == 404
