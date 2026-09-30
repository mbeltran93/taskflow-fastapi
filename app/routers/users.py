import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserCreate, UserRead
from app.services import users as users_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserRead],
    summary="List users",
    description="Returns every registered user. Read-only, no authentication required.",
)
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    return users_service.list_users(db)  # type: ignore[return-value]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
    description="Creates a new user account. This is the sign-up endpoint used before "
    "`/api/auth/login` can issue a token for that user.",
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if users_service.get_user_by_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    return users_service.create_user(db, payload)  # type: ignore[return-value]


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user",
    description="Returns a single user by id, or 404 if it doesn't exist.",
)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> UserRead:
    user = users_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user  # type: ignore[return-value]
