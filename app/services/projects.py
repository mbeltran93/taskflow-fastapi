import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def get_project(db: Session, project_id: uuid.UUID) -> Project | None:
    return db.get(Project, project_id)


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.name)))


def create_project(db: Session, data: ProjectCreate, owner_id: uuid.UUID) -> Project:
    project = Project(name=data.name, description=data.description, owner_id=owner_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()
