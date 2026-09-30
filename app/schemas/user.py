import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, examples=["Ada Lovelace"])
    email: EmailStr = Field(..., examples=["ada@example.com"])


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128, examples=["supersecret123"])


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
