from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Project, Task, User  # noqa: F401  (register models on Base)

# In-memory SQLite shared across the single test connection, so the whole test
# suite runs fast and without needing a real Postgres instance.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _reset_schema() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def user_payload() -> dict:
    return {"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret123"}


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, user_payload: dict) -> dict:
    response = await client.post("/api/users", json=user_payload)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, user_payload: dict, registered_user: dict) -> str:
    response = await client.post(
        "/api/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}
