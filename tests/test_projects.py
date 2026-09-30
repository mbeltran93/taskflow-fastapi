import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_and_get_project(client: AsyncClient, auth_headers: dict):
    create_response = await client.post(
        "/api/projects",
        json={"name": "Website Redesign", "description": "Revamp the marketing site"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    project = create_response.json()
    assert project["name"] == "Website Redesign"

    get_response = await client.get(f"/api/projects/{project['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == project["id"]


async def test_list_projects(client: AsyncClient, auth_headers: dict):
    await client.post("/api/projects", json={"name": "Project A"}, headers=auth_headers)
    await client.post("/api/projects", json={"name": "Project B"}, headers=auth_headers)

    response = await client.get("/api/projects")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Project A" in names
    assert "Project B" in names


async def test_update_project(client: AsyncClient, auth_headers: dict):
    create_response = await client.post(
        "/api/projects", json={"name": "Old Name"}, headers=auth_headers
    )
    project_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/projects/{project_id}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "New Name"


async def test_delete_project(client: AsyncClient, auth_headers: dict):
    create_response = await client.post(
        "/api/projects", json={"name": "Throwaway"}, headers=auth_headers
    )
    project_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 404


async def test_get_unknown_project_returns_404(client: AsyncClient):
    response = await client.get(f"/api/projects/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_create_project_without_token_returns_401(client: AsyncClient):
    response = await client.post("/api/projects", json={"name": "Nope"})
    assert response.status_code == 401
