import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, examples=["Write the API docs"])
    description: str | None = Field(None, examples=["Document every endpoint in the README"])
    due_date: date | None = Field(None, examples=["2026-12-31"])


class TaskCreate(TaskBase):
    project_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    status: TaskStatus = TaskStatus.TODO


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: TaskStatus
    project_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
