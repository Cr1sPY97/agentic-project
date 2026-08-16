from typing import Optional
from pydantic import BaseModel, EmailStr
from app.db.models import RoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
    role: RoleEnum


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    username_or_email: str
    password: str
