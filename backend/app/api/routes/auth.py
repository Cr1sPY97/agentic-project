from datetime import timedelta
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, RoleEnum
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token, LoginRequest
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.api.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account with role-based access.
    The first registered user is automatically provisioned as ADMIN.
    """
    user_repo = UserRepository(db)
    if user_repo.get_by_username(user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_in.username}' is already registered.",
        )
    if user_repo.get_by_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_in.email}' is already registered.",
        )

    # First user auto-admin bootstrap
    assigned_role = user_in.role.value
    if user_repo.count() == 0:
        assigned_role = RoleEnum.ADMIN.value

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=assigned_role,
        is_active=True,
    )
    created_user = user_repo.create(user)

    audit_service = AuditService(db)
    audit_service.log_event(
        action="USER_REGISTERED",
        resource_type="user",
        resource_id=str(created_user.id),
        actor=created_user,
        details={"username": created_user.username, "role": created_user.role},
    )

    return created_user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2 compatible token login for Swagger UI and API clients.
    Authenticates username and password, returning JWT access token.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_username_or_email(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_payload = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
    }
    access_token = create_access_token(token_payload, expires_delta=access_token_expires)

    client_ip = request.client.host if request.client else "unknown"
    audit_service = AuditService(db)
    audit_service.log_event(
        action="LOGIN",
        resource_type="auth",
        resource_id=str(user.id),
        actor=user,
        ip_address=client_ip,
        details={"username": user.username, "role": user.role},
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Fetch profile of currently authenticated user."""
    return current_user
