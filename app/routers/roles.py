"""Role and user-role management endpoints."""

from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=List[schemas.RoleResponse])
def get_all_roles(db: Session = Depends(get_db)):
    """Get all available roles (Student, Teacher, Admin)."""
    return db.query(models.Role).all()


@router.get("/user/{user_uuid}", response_model=List[schemas.UserRoleResponse])
def get_user_roles(user_uuid: str, db: Session = Depends(get_db)):
    """Get current active roles for a specific user."""
    roles = (
        db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == user_uuid, models.UserRole.is_current == True
        )
        .all()
    )

    # Populate role_name from joined Role
    return [
        {
            "id": r.id,
            "user_uuid": r.user_uuid,
            "role_id": r.role_id,
            "role_name": r.role.name,
            "is_current": r.is_current,
            "effective_date": r.effective_date,
            "end_date": r.end_date,
            "created_date": r.created_date,
        }
        for r in roles
    ]


@router.get("/user/{user_uuid}/history", response_model=schemas.UserRoleHistoryResponse)
def get_user_role_history(user_uuid: str, db: Session = Depends(get_db)):
    """Get complete role history for a user (current + historical)."""
    user = (
        db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == True)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    all_roles = (
        db.query(models.UserRole)
        .join(models.Role)
        .filter(models.UserRole.user_uuid == user_uuid)
        .order_by(models.UserRole.effective_date.desc())
        .all()
    )

    current_roles = [r.role.name for r in all_roles if r.is_current]

    history = [
        {
            "id": r.id,
            "user_uuid": r.user_uuid,
            "role_id": r.role_id,
            "role_name": r.role.name,
            "is_current": r.is_current,
            "effective_date": r.effective_date,
            "end_date": r.end_date,
            "created_date": r.created_date,
        }
        for r in all_roles
    ]

    return {
        "user_uuid": user_uuid,
        "user_full_name": f"{user.first_name} {user.last_name}",
        "current_roles": current_roles,
        "history": history,
    }


@router.put("/user/{user_uuid}", response_model=List[schemas.UserRoleResponse])
def update_user_roles(
    user_uuid: str,
    role_assignment: schemas.UserRoleAssignment,
    db: Session = Depends(get_db),
):
    """
    Update user roles using SCD Type 2 pattern.
    Replaces all current roles with the provided list.
    """
    # 1. Verify user exists
    user = (
        db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == True)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Verify all role IDs are valid
    valid_roles = (
        db.query(models.Role).filter(models.Role.id.in_(role_assignment.role_ids)).all()
    )
    if len(valid_roles) != len(role_assignment.role_ids):
        raise HTTPException(status_code=400, detail="One or more invalid role IDs")

    # 3. Get current active roles
    current_roles = (
        db.query(models.UserRole)
        .filter(
            models.UserRole.user_uuid == user_uuid, models.UserRole.is_current == True
        )
        .all()
    )

    current_role_ids = {r.role_id for r in current_roles}
    new_role_ids = set(role_assignment.role_ids)

    now = datetime.now(timezone.utc)

    # 4. Expire roles that are being removed
    roles_to_remove = current_role_ids - new_role_ids
    for role in current_roles:
        if role.role_id in roles_to_remove:
            role.is_current = False
            role.end_date = now
            role.updated_date = now

    # 5. Add new roles
    roles_to_add = new_role_ids - current_role_ids
    for role_id in roles_to_add:
        new_assignment = models.UserRole(
            user_uuid=user_uuid,
            role_id=role_id,
            is_current=True,
            effective_date=now,
            created_date=now,
            updated_date=now,
        )
        db.add(new_assignment)

    db.commit()

    # 6. Return updated current roles
    updated_roles = (
        db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == user_uuid, models.UserRole.is_current == True
        )
        .all()
    )

    return [
        {
            "id": r.id,
            "user_uuid": r.user_uuid,
            "role_id": r.role_id,
            "role_name": r.role.name,
            "is_current": r.is_current,
            "effective_date": r.effective_date,
            "end_date": r.end_date,
            "created_date": r.created_date,
        }
        for r in updated_roles
    ]


@router.get("/users/by-role/{role_name}", response_model=List[schemas.UserResponse])
def get_users_by_role(role_name: str, db: Session = Depends(get_db)):
    """Get all users with a specific role (e.g., all Teachers)."""
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")

    user_uuids = (
        db.query(models.UserRole.user_uuid)
        .filter(models.UserRole.role_id == role.id, models.UserRole.is_current == True)
        .all()
    )

    uuid_list = [u[0] for u in user_uuids]

    users = (
        db.query(models.User)
        .filter(models.User.user_uuid.in_(uuid_list), models.User.is_current == True)
        .all()
    )

    return users
