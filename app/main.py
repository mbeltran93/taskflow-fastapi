from fastapi import FastAPI

from app.config import get_settings
from app.routers import auth, projects, tasks, users

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "TaskFlow is a small, portfolio-sized clone of a Trello/Jira-style task "
        "manager: users own projects, and projects contain tasks that move through "
        "TODO -> IN_PROGRESS -> DONE. Write operations require a JWT obtained from "
        "`/api/auth/login`."
    ),
    version="0.1.0",
    contact={"name": "mbeltran93", "url": "https://github.com/mbeltran93"},
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health", tags=["health"], summary="Health check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
