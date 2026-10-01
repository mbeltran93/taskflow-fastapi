# TaskFlow API (FastAPI)

A small, portfolio-sized clone of a Trello/Jira-style task manager: **users**
own **projects**, and projects contain **tasks** that move through
`TODO -> IN_PROGRESS -> DONE`.

This is the Python/FastAPI implementation of the TaskFlow domain, part of a
set of portfolio backends that all model the same domain and expose the same
REST contract (see [API contract](#api-endpoints) below) so they're directly
comparable across stacks.

## Stack

- **FastAPI** for the HTTP layer, with auto-generated OpenAPI docs at `/docs`.
- **SQLAlchemy 2.x** (typed `Mapped[...]` models) as the ORM.
- **Pydantic v2** for request/response schemas and settings.
- **PostgreSQL** as the database, **Alembic** for migrations.
- **JWT** auth (`python-jose`) and **bcrypt** password hashing (`passlib`).
- **pytest** + **httpx** (async test client) for the test suite, run against
  an in-memory SQLite database so tests don't need Postgres running.
- **Docker** + **docker-compose** to run the whole stack with one command.

## Project layout

```
app/
  main.py          # FastAPI app, routers wiring
  config.py         # Settings (env vars via pydantic-settings)
  core/
    security.py     # password hashing + JWT encode/decode
    deps.py          # get_current_user dependency (Bearer token -> User)
  db/
    base.py          # SQLAlchemy declarative base
    session.py        # engine, SessionLocal, get_db dependency
    types.py          # cross-dialect GUID column type (Postgres UUID / SQLite CHAR)
  models/            # SQLAlchemy ORM models (User, Project, Task)
  schemas/           # Pydantic request/response models
  services/          # business logic / DB queries, framework-agnostic
  routers/           # FastAPI path operations (auth, users, projects, tasks)
alembic/             # migrations (env.py reads DATABASE_URL from app settings)
tests/               # pytest suite (httpx.AsyncClient against the ASGI app)
```

The layering is: **routers** validate input, resolve dependencies (DB
session, current user) and call **services**; **services** contain the
actual queries/business rules and talk to **models**; **schemas** are the
Pydantic shapes that cross the HTTP boundary.

## Running it

### With Docker (recommended)

Requires Docker and Docker Compose.

```bash
docker compose up --build
```

This starts Postgres and the API. On boot, the API container runs
`alembic upgrade head` and then starts `uvicorn`. Once it's up:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

### Locally (without Docker)

Requires Python 3.12+ and a running Postgres instance.

```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows (git-bash); use .venv/bin/activate on Linux/macOS
pip install -r requirements-dev.txt

cp .env.example .env                 # adjust DATABASE_URL if needed
alembic upgrade head
uvicorn app.main:app --reload
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

Most tests run against an in-memory SQLite database (schema created/dropped
per test), so they don't require Postgres or Docker to be running. They
cover:

- registration + login, wrong password / unknown user (`401`)
- duplicate registration (`409`)
- calling a write endpoint without a token (`401`)
- project CRUD (create/list/get/update/delete) and 404 on unknown id
- task CRUD, filtering by `projectId`/`status`, the `PATCH /status` endpoint,
  and 404s for unknown project/task

### Real-Postgres integration tests

`tests/test_postgres_integration.py` spins up a disposable Postgres
container with [Testcontainers](https://testcontainers-python.readthedocs.io/),
runs the project's real Alembic migrations against it, and drives the app
through `httpx` exactly like the SQLite tests above -- but against a real
database engine. This covers things the SQLite suite structurally can't:

- the Alembic migration actually applying cleanly to Postgres,
- the native Postgres `UUID` column path of the cross-dialect `GUID` type
  (SQLite only ever exercises the `CHAR(32)` fallback),
- real foreign-key enforcement: deleting a project cascades to its tasks
  (`ON DELETE CASCADE`), and deleting a user nulls out `assignee_id` on their
  tasks (`ON DELETE SET NULL`) -- SQLite doesn't enforce FKs by default, so
  this is otherwise untested.

These tests need Docker running locally (same requirement as `docker compose
up`) and are automatically **skipped** if a container can't be started, so
`pytest` still passes on a machine without Docker.

## Trying it with curl

```bash
# 1. Register a user
curl -s -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret123"}'

# 2. Log in to get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ada@example.com", "password": "supersecret123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 3. Create a project (requires the token)
PROJECT_ID=$(curl -s -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Website Redesign", "description": "Revamp the marketing site"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 4. Create a task in that project
curl -s -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d "{\"title\": \"Write the API docs\", \"project_id\": \"$PROJECT_ID\"}"
```

## Trying it with Postman

[`postman_collection.json`](postman_collection.json) has the same flow as the
curl walkthrough above, plus a couple of negative cases, as a ready-to-run
Postman collection:

1. register a user
2. log in
3. create a project
4. create a task
5. list tasks filtered by `projectId`/`status`
6. update a task's status
7. call a write endpoint without a token (expects `401`)
8. fetch an unknown task id (expects `404`)

To import it:

1. Open Postman -> **Import** -> select `postman_collection.json` (or drag
   it into the app).
2. The collection ships with a `baseUrl` variable defaulting to
   `http://localhost:8000`, so it works out of the box against either
   `docker compose up` or the local `uvicorn --reload` setup -- edit the
   collection's variables if your API runs elsewhere.
3. Run requests in order (or use **Runner** to run the whole collection
   top to bottom). The "Login" request's Tests script saves the returned
   JWT into the `token` collection variable automatically, and every
   authenticated request after it reads that variable via
   `Authorization: Bearer {{token}}` -- no manual copy/paste needed. The
   "Register user" request similarly generates a unique email per run (so
   the collection can be re-run without hitting `409 Conflict`), and
   "Create project"/"Create task" save the created ids for the requests
   that depend on them.

## API endpoints

All write routes (`POST`/`PUT`/`PATCH`/`DELETE`, except registration and
login) require `Authorization: Bearer <token>`.

| Method | Path                          | Auth | Description                          |
|--------|-------------------------------|------|--------------------------------------|
| POST   | `/api/auth/login`             | No   | Exchanges email+password for a JWT   |
| GET    | `/api/users`                  | No   | List users                           |
| POST   | `/api/users`                  | No   | Register a user                      |
| GET    | `/api/users/{id}`             | No   | Get a user by id                     |
| GET    | `/api/projects`               | No   | List projects                        |
| POST   | `/api/projects`               | Yes  | Create a project (owned by caller)   |
| GET    | `/api/projects/{id}`          | No   | Get a project by id                  |
| PUT    | `/api/projects/{id}`          | Yes  | Update a project                     |
| DELETE | `/api/projects/{id}`          | Yes  | Delete a project (cascades to tasks) |
| GET    | `/api/tasks?projectId=&status=` | No | List tasks, optionally filtered      |
| POST   | `/api/tasks`                  | Yes  | Create a task                        |
| GET    | `/api/tasks/{id}`             | No   | Get a task by id                     |
| PUT    | `/api/tasks/{id}`             | Yes  | Update a task                        |
| DELETE | `/api/tasks/{id}`             | Yes  | Delete a task                        |
| PATCH  | `/api/tasks/{id}/status`      | Yes  | Update only a task's status          |
| GET    | `/health`                     | No   | Liveness check                       |

Full interactive documentation (request/response schemas, examples, try-it-out)
is available at `/docs` once the app is running.

## Known limitations

- Authorization is purely "has a valid token" — there is no ownership check
  (e.g. any authenticated user can update/delete any project or task, not
  just their own). Adding that would mean threading owner/assignee checks
  through the services layer.
- No refresh tokens or token revocation; JWTs are valid for 24h and that's it.
- No rate limiting or pagination on list endpoints — fine for a portfolio
  demo, not for a dataset of meaningful size.
- The `GUID` column type stores UUIDs as native `UUID` on Postgres but as
  plain `CHAR(32)` on SQLite, purely so the test suite can run fast without a
  real Postgres; this trade-off is invisible to the API but is a deliberate
  deviation from "one database everywhere".
