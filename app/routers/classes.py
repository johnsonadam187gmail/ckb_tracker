"""Class schedule management endpoints."""

from typing import Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/classes", tags=["classes"])


@router.post("/", response_model=schemas.ClassResponse)
def create_class(class_data: schemas.ClassCreate, db: Session = Depends(get_db)):
    """Create new class schedule."""
    new_uuid = str(uuid.uuid4())

    db_class = models.ClassSchedule(
        **class_data.model_dump(), class_uuid=new_uuid, is_current=True
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@router.get("/", response_model=list[schemas.ClassResponse])
def get_current_classes(db: Session = Depends(get_db)):
    """Fetch all active classes."""
    return (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_current == True)
        .all()
    )


@router.put("/{class_uuid}", response_model=schemas.ClassResponse)
def update_class_schedule(
    class_uuid: str,
    class_name: str = Form(...),
    day: str = Form(...),
    time: str = Form(...),
    weighting: float = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Update class using SCD Type 2 pattern."""
    now = datetime.now(timezone.utc)

    old_version = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.class_uuid == class_uuid,
            models.ClassSchedule.is_current == True,
        )
        .first()
    )

    if not old_version:
        raise HTTPException(status_code=404, detail="Class not found")

    old_version.is_current = False
    old_version.end_date = now

    new_version = models.ClassSchedule(
        class_uuid=class_uuid,
        class_name=class_name,
        day=day,
        time=time,
        weighting=weighting,
        description=description,
        is_current=True,
        effective_date=now,
        created_date=old_version.created_date,
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version
