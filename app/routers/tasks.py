import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskStatusUpdate, TaskUpdate
from app.services import projects as projects_service
from app.services import tasks as tasks_service
from app.services import users as users_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _get_task_or_404(db: Session, task_id: uuid.UUID):
    task = tasks_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get(
    "",
    response_model=list[TaskRead],
    summary="List tasks",
    description="Returns tasks, optionally filtered by `projectId` and/or `status`. "
    "Read-only, no authentication required.",
)
def list_tasks(
    projectId: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    db: Session = Depends(get_db),
) -> list[TaskRead]:
    return tasks_service.list_tasks(db, project_id=projectId, status=status)  # type: ignore[return-value]


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description="Creates a new task under an existing project, optionally assigned to a user. "
    "Requires a bearer token.",
)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    if projects_service.get_project(db, payload.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if payload.assignee_id is not None and users_service.get_user(db, payload.assignee_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")
    return tasks_service.create_task(db, payload)  # type: ignore[return-value]


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Get a task",
    description="Returns a single task by id, or 404 if it doesn't exist.",
)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)) -> TaskRead:
    return _get_task_or_404(db, task_id)  # type: ignore[return-value]


@router.put(
    "/{task_id}",
    response_model=TaskRead,
    summary="Update a task",
    description="Partially updates a task's fields (title, description, status, assignee, "
    "due date). Requires a bearer token.",
)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = _get_task_or_404(db, task_id)
    if payload.assignee_id is not None and users_service.get_user(db, payload.assignee_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")
    return tasks_service.update_task(db, task, payload)  # type: ignore[return-value]


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Deletes a task. Requires a bearer token.",
)
def delete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = _get_task_or_404(db, task_id)
    tasks_service.delete_task(db, task)


@router.patch(
    "/{task_id}/status",
    response_model=TaskRead,
    summary="Update a task's status",
    description="Moves a task to TODO, IN_PROGRESS or DONE. Requires a bearer token.",
)
def update_task_status(
    task_id: uuid.UUID,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = _get_task_or_404(db, task_id)
    return tasks_service.update_task_status(db, task, payload)  # type: ignore[return-value]
