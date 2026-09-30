from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.services.users import get_user_by_email
from sqlalchemy.orm import Session


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def issue_token_for(user: User) -> str:
    return create_access_token(subject=str(user.id))
