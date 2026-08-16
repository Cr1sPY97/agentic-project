from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, RoleEnum
from app.schemas.user import UserResponse, UserUpdateRole
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.api.dependencies import require_roles

router = APIRouter()


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """List all registered users. Restricted to ADMIN."""
    user_repo = UserRepository(db)
    return user_repo.list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieve user details by ID. Restricted to ADMIN."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    return user


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    role_in: UserUpdateRole,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """Update role for a user. Restricted to ADMIN."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")

    old_role = user.role
    updated_user = user_repo.update_role(user, role_in.role)

    audit_service = AuditService(db)
    audit_service.log_event(
        action="USER_ROLE_UPDATED",
        resource_type="user",
        resource_id=str(user.id),
        actor=current_user,
        details={"old_role": old_role, "new_role": updated_user.role},
    )

    return updated_user
