from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.db.models import RoleEnum


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    role: RoleEnum = RoleEnum.VIEWER


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdateRole(BaseModel):
    role: RoleEnum


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
