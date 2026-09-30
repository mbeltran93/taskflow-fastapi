import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_users(client: AsyncClient, registered_user: dict):
    response = await client.get("/api/users")
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert registered_user["email"] in emails


async def test_get_user_by_id(client: AsyncClient, registered_user: dict):
    response = await client.get(f"/api/users/{registered_user['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == registered_user["id"]


async def test_get_unknown_user_returns_404(client: AsyncClient):
    response = await client.get(f"/api/users/{uuid.uuid4()}")
    assert response.status_code == 404
