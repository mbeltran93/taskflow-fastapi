"""Integration tests against a *real* Postgres instance (via Testcontainers).

Every other test in this suite runs against in-memory SQLite (see
``tests/conftest.py``) for speed, which is great for day-to-day TDD but never
actually exercises:

- the Alembic migration applied to a real database engine (only ever run
  manually / inside the Docker image, never under test),
- the native Postgres ``UUID`` column path of the cross-dialect ``GUID``
  type (SQLite only ever exercises the ``CHAR(32)`` fallback),
- real foreign-key enforcement -- SQLite does not enforce FKs unless
  ``PRAGMA foreign_keys=ON`` is set, and the test engine in conftest.py never
  sets it, so ``ON DELETE CASCADE``/``ON DELETE SET NULL`` have never actually
  been verified end-to-end.

These tests spin up a disposable Postgres container, run the project's real
Alembic migrations against it, and drive the ASGI app through httpx exactly
like the rest of the suite, but talking to that real database.

Requires Docker to be running locally; each test is skipped (not failed) if a
container can't be started, so the rest of the suite still runs fine on a
machine without Docker.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_db
from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:  # pragma: no cover - exercised only if the extra isn't installed
    PostgresContainer = None  # type: ignore[assignment]


@pytest.fixture(scope="module")
def postgres_url() -> Generator[str, None, None]:
    """Start a throwaway Postgres container and apply the real migrations to it."""
    if PostgresContainer is None:
        pytest.skip("testcontainers[postgres] is not installed")

    try:
        container = PostgresContainer("postgres:16-alpine", driver="psycopg")
        container.start()
    except Exception as exc:  # noqa: BLE001 - Docker not available/running, etc.
        pytest.skip(f"could not start a Postgres container: {exc}")
        return  # pragma: no cover

    try:
        url = container.get_connection_url()
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            env={**os.environ, "DATABASE_URL": url},
            check=True,
            capture_output=True,
            text=True,
        )
        yield url
    finally:
        container.stop()


@pytest.fixture(scope="module")
def postgres_sessionmaker(postgres_url: str) -> sessionmaker:
    engine = create_engine(postgres_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session(postgres_sessionmaker: sessionmaker) -> Generator[Session, None, None]:
    db = postgres_sessionmaker()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _use_postgres_for_app(postgres_sessionmaker: sessionmaker) -> Generator[None, None, None]:
    """Point the FastAPI app's `get_db` dependency at the real Postgres DB for this module."""

    def _override() -> Generator[Session, None, None]:
        db = postgres_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[get_db] = previous
        else:
            app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    email = f"pg-{uuid.uuid4()}@example.com"
    password = "supersecret123"
    register = await client.post(
        "/api/users", json={"name": "PG Tester", "email": email, "password": password}
    )
    assert register.status_code == 201
    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


async def test_full_flow_against_real_postgres(client: AsyncClient, auth_headers: dict) -> None:
    """Register/login/create project/create task/filter, exactly like the SQLite suite,
    but this time against a real Postgres database with native UUID columns."""
    project_resp = await client.post(
        "/api/projects", json={"name": "Postgres Smoke Test"}, headers=auth_headers
    )
    assert project_resp.status_code == 201
    project = project_resp.json()
    # On Postgres the GUID type stores native UUIDs; confirm the id really parses as one.
    assert uuid.UUID(project["id"])

    task_resp = await client.post(
        "/api/tasks",
        json={"title": "Verify native UUID path", "project_id": project["id"]},
        headers=auth_headers,
    )
    assert task_resp.status_code == 201
    task = task_resp.json()

    listed = await client.get(f"/api/tasks?projectId={project['id']}&status=TODO")
    assert listed.status_code == 200
    assert [t["id"] for t in listed.json()] == [task["id"]]


async def test_deleting_project_cascades_to_tasks_on_real_postgres(
    client: AsyncClient, auth_headers: dict, db_session: Session
) -> None:
    """The Task model declares `ForeignKey("projects.id", ondelete="CASCADE")`.
    SQLite never enforces this in the existing suite (no PRAGMA foreign_keys=ON),
    so this is the first time that CASCADE behaviour is actually verified."""
    project_resp = await client.post(
        "/api/projects", json={"name": "Cascade Test"}, headers=auth_headers
    )
    project_id = project_resp.json()["id"]

    task_resp = await client.post(
        "/api/tasks", json={"title": "Will be cascaded", "project_id": project_id}, headers=auth_headers
    )
    task_id = task_resp.json()["id"]

    delete_resp = await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    remaining = db_session.execute(
        text("SELECT COUNT(*) FROM tasks WHERE id = :id"), {"id": task_id}
    ).scalar()
    assert remaining == 0


async def test_deleting_assignee_sets_task_assignee_null_on_real_postgres(
    client: AsyncClient, auth_headers: dict, db_session: Session
) -> None:
    """The Task model declares `ForeignKey("users.id", ondelete="SET NULL")` for
    `assignee_id`. Same gap as the cascade test above: never verified against a
    real FK-enforcing database until now."""
    assignee_email = f"assignee-{uuid.uuid4()}@example.com"
    assignee_resp = await client.post(
        "/api/users",
        json={"name": "Temp Assignee", "email": assignee_email, "password": "supersecret123"},
    )
    assignee_id = assignee_resp.json()["id"]

    project_resp = await client.post(
        "/api/projects", json={"name": "Set Null Test"}, headers=auth_headers
    )
    project_id = project_resp.json()["id"]

    task_resp = await client.post(
        "/api/tasks",
        json={
            "title": "Assigned task",
            "project_id": project_id,
            "assignee_id": assignee_id,
        },
        headers=auth_headers,
    )
    task_id = task_resp.json()["id"]
    assert task_resp.json()["assignee_id"] == assignee_id

    db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": assignee_id})
    db_session.commit()

    refreshed = await client.get(f"/api/tasks/{task_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["assignee_id"] is None
