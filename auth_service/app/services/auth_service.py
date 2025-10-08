from sqlalchemy.orm import Session

from app.repositories import user_repository
from app.core.security import verify_password

def authenticate_user(db: Session, email: str, password: str):
    user = user_repository.get_user_by_email(db, email=email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user
