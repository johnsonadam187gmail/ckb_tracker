"""
Database query helper functions to reduce duplication.
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from . import models


def get_current_users(db: Session) -> List[models.User]:
    """Fetch all current (active) user records."""
    return db.query(models.User).filter(models.User.is_current == True).all()


def get_current_classes(db: Session) -> List[models.ClassSchedule]:
    """Fetch all current (active) class schedules."""
    return (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_current == True)
        .all()
    )


def get_user_by_uuid(
    db: Session, user_uuid: str, current_only: bool = True
) -> Optional[models.User]:
    """
    Fetch user by UUID.

    Args:
        db: Database session
        user_uuid: User's anchor UUID
        current_only: If True, only return current version (default)

    Returns:
        User model instance or None
    """
    query = db.query(models.User).filter(models.User.user_uuid == user_uuid)

    if current_only:
        query = query.filter(models.User.is_current == True)

    return query.first()


def get_class_by_uuid(
    db: Session, class_uuid: str, current_only: bool = True
) -> Optional[models.ClassSchedule]:
    """
    Fetch class by UUID.

    Args:
        db: Database session
        class_uuid: Class anchor UUID
        current_only: If True, only return current version (default)

    Returns:
        ClassSchedule model instance or None
    """
    query = db.query(models.ClassSchedule).filter(
        models.ClassSchedule.class_uuid == class_uuid
    )

    if current_only:
        query = query.filter(models.ClassSchedule.is_current == True)

    return query.first()
