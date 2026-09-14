"""User API routes.

Users are provisioned via Databricks Apps SSO (get_or_create on first request).
These endpoints only expose self-service profile access and authenticated
email lookup for sharing — no public list/create/update of arbitrary users.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserUpdate, UserResponse
from app.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def _is_admin(user: User) -> bool:
    return (user.role or "").lower() == "admin"


# NOTE: /me route MUST be defined BEFORE /{user_id} to avoid "me" being parsed as UUID
@router.get("/me", response_model=UserResponse)
async def get_current_user_me(
    current_user: User = Depends(get_current_user),
):
    """Get the current authenticated user (SSO-provisioned)."""
    return current_user


@router.get("/email/{email}", response_model=UserResponse)
async def get_user_by_email(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Look up a user by email for sharing flows. Requires authentication."""
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a user by ID. Callers may only read themselves unless admin."""
    if current_user.user_id != user_id and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a user profile. Non-admins may only update their own full_name."""
    if current_user.user_id != user_id and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.model_dump(exclude_unset=True)

    if not _is_admin(current_user):
        # Self-service: display name only
        update_data = {k: v for k, v in update_data.items() if k == "full_name"}

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user
