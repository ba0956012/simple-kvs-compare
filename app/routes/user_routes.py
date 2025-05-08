from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth import get_current_user_obj, get_password_hash, verify_password, USERS

router = APIRouter()

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/change-password")
def change_password(data: ChangePasswordRequest, current_user: dict = Depends(get_current_user_obj)):
    username = current_user["username"]
    if not verify_password(data.old_password, USERS[username]["hashed_password"]):
        raise HTTPException(status_code=400, detail="Old password incorrect")

    USERS[username]["hashed_password"] = get_password_hash(data.new_password)
    return {"message": "Password updated successfully"}
