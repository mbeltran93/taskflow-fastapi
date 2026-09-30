import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_then_login_returns_token(client: AsyncClient, user_payload: dict):
    register_response = await client.post("/api/users", json=user_payload)
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == user_payload["email"]
    assert "password" not in body
    assert "hashed_password" not in body

    login_response = await client.post(
        "/api/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert login_response.status_code == 200
    token_body = login_response.json()
    assert token_body["token"]
    assert token_body["token_type"] == "bearer"


async def test_login_with_wrong_password_returns_401(client: AsyncClient, registered_user, user_payload):
    response = await client.post(
        "/api/auth/login", json={"email": user_payload["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_with_unknown_email_returns_401(client: AsyncClient):
    response = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert response.status_code == 401


async def test_duplicate_registration_returns_409(client: AsyncClient, registered_user, user_payload):
    response = await client.post("/api/users", json=user_payload)
    assert response.status_code == 409


async def test_write_endpoint_without_token_returns_401(client: AsyncClient):
    response = await client.post(
        "/api/projects", json={"name": "No auth project", "description": None}
    )
    assert response.status_code == 401
