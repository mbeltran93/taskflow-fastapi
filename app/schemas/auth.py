from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["ada@example.com"])
    password: str = Field(..., examples=["supersecret123"])


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
