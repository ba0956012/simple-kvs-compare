from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User
from app.auth import get_current_user_obj, get_password_hash, verify_password

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_superuser: bool = False


@router.post("/create")
def create_user(
    data: CreateUserRequest,
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db),
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Only superusers can create accounts"
        )

    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        is_superuser=data.is_superuser,
    )
    db.add(new_user)
    db.commit()
    return {"message": f"User '{data.username}' created successfully"}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_obj),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
