import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import projects as projects_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_project_or_404(db: Session, project_id: uuid.UUID):
    project = projects_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get(
    "",
    response_model=list[ProjectRead],
    summary="List projects",
    description="Returns every project. Read-only, no authentication required.",
)
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return projects_service.list_projects(db)  # type: ignore[return-value]


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    description="Creates a new project owned by the authenticated user. Requires a bearer token.",
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    return projects_service.create_project(db, payload, owner_id=current_user.id)  # type: ignore[return-value]


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get a project",
    description="Returns a single project by id, or 404 if it doesn't exist.",
)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)) -> ProjectRead:
    return _get_project_or_404(db, project_id)  # type: ignore[return-value]


@router.put(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Update a project",
    description="Partially updates a project's name and/or description. Requires a bearer token.",
)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = _get_project_or_404(db, project_id)
    return projects_service.update_project(db, project, payload)  # type: ignore[return-value]


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Deletes a project and cascades to its tasks. Requires a bearer token.",
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    project = _get_project_or_404(db, project_id)
    projects_service.delete_project(db, project)
