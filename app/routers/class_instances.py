"""Class instance (lessons) management endpoints."""

from typing import Optional, List
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/class-instances", tags=["class-instances"])


@router.post("/", response_model=schemas.ClassInstanceResponse)
def create_class_instance(
    instance_data: schemas.ClassInstanceCreate, db: Session = Depends(get_db)
):
    """Create or update a class instance (upsert pattern).

    If a class instance already exists for the given class_id and class_date,
    it will be updated. Otherwise, a new instance will be created.
    """
    # Check if instance already exists
    existing = (
        db.query(models.ClassInstance)
        .filter(
            models.ClassInstance.class_id == instance_data.class_id,
            models.ClassInstance.class_date == instance_data.class_date,
        )
        .first()
    )

    if existing:
        # Update existing instance
        for key, value in instance_data.model_dump(exclude_unset=True).items():
            if key not in [
                "class_id",
                "class_date",
            ]:  # Don't update unique constraint fields
                setattr(existing, key, value)

        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)

        # Populate joined fields for response
        response_data = schemas.ClassInstanceResponse.model_validate(existing)
        response_data.class_name = (
            existing.class_schedule.class_name if existing.class_schedule else None
        )
        if existing.teacher_uuid and existing.teacher:
            response_data.teacher_name = (
                f"{existing.teacher.first_name} {existing.teacher.last_name}"
            )

        return response_data
    else:
        # Create new instance
        db_instance = models.ClassInstance(**instance_data.model_dump())

        try:
            db.add(db_instance)
            db.commit()
            db.refresh(db_instance)

            # Populate joined fields for response
            response_data = schemas.ClassInstanceResponse.model_validate(db_instance)
            response_data.class_name = (
                db_instance.class_schedule.class_name
                if db_instance.class_schedule
                else None
            )
            if db_instance.teacher_uuid and db_instance.teacher:
                response_data.teacher_name = (
                    f"{db_instance.teacher.first_name} {db_instance.teacher.last_name}"
                )

            return response_data
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Class instance for this class and date already exists.",
            )


@router.get("/", response_model=List[schemas.ClassInstanceResponse])
def get_class_instances(
    class_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    teacher_uuid: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all class instances with optional filters."""
    query = db.query(models.ClassInstance)

    if class_id:
        query = query.filter(models.ClassInstance.class_id == class_id)
    if start_date:
        query = query.filter(models.ClassInstance.class_date >= start_date)
    if end_date:
        query = query.filter(models.ClassInstance.class_date <= end_date)
    if teacher_uuid:
        query = query.filter(models.ClassInstance.teacher_uuid == teacher_uuid)

    instances = query.order_by(models.ClassInstance.class_date.desc()).all()

    # Populate joined fields
    for instance in instances:
        instance.class_name = (
            instance.class_schedule.class_name if instance.class_schedule else None
        )
        if instance.teacher_uuid and instance.teacher:
            instance.teacher_name = (
                f"{instance.teacher.first_name} {instance.teacher.last_name}"
            )

    return instances


@router.get("/{instance_id}", response_model=schemas.ClassInstanceResponse)
def get_class_instance(instance_id: int, db: Session = Depends(get_db)):
    """Get a specific class instance by ID."""
    instance = (
        db.query(models.ClassInstance)
        .filter(models.ClassInstance.id == instance_id)
        .first()
    )

    if not instance:
        raise HTTPException(status_code=404, detail="Class instance not found")

    # Populate joined fields
    instance.class_name = (
        instance.class_schedule.class_name if instance.class_schedule else None
    )
    if instance.teacher_uuid and instance.teacher:
        instance.teacher_name = (
            f"{instance.teacher.first_name} {instance.teacher.last_name}"
        )

    return instance


@router.get("/by-date/", response_model=schemas.ClassInstanceResponse)
def get_class_instance_by_date(
    class_id: int = Query(...),
    class_date: date = Query(...),
    db: Session = Depends(get_db),
):
    """Get a class instance by class_id and class_date."""
    instance = (
        db.query(models.ClassInstance)
        .filter(
            models.ClassInstance.class_id == class_id,
            models.ClassInstance.class_date == class_date,
        )
        .first()
    )

    if not instance:
        raise HTTPException(
            status_code=404,
            detail=f"No class instance found for class {class_id} on {class_date}",
        )

    # Populate joined fields
    instance.class_name = (
        instance.class_schedule.class_name if instance.class_schedule else None
    )
    if instance.teacher_uuid and instance.teacher:
        instance.teacher_name = (
            f"{instance.teacher.first_name} {instance.teacher.last_name}"
        )

    return instance


@router.put("/{instance_id}", response_model=schemas.ClassInstanceResponse)
def update_class_instance(
    instance_id: int,
    update_data: schemas.ClassInstanceUpdate,
    db: Session = Depends(get_db),
):
    """Update a class instance (lesson information)."""
    instance = (
        db.query(models.ClassInstance)
        .filter(models.ClassInstance.id == instance_id)
        .first()
    )

    if not instance:
        raise HTTPException(status_code=404, detail="Class instance not found")

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(instance, key, value)

    instance.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(instance)

    # Populate joined fields
    instance.class_name = (
        instance.class_schedule.class_name if instance.class_schedule else None
    )
    if instance.teacher_uuid and instance.teacher:
        instance.teacher_name = (
            f"{instance.teacher.first_name} {instance.teacher.last_name}"
        )

    return instance


@router.delete("/{instance_id}")
def delete_class_instance(instance_id: int, db: Session = Depends(get_db)):
    """Delete a class instance.

    Will fail if attendance records are linked to this instance.
    """
    instance = (
        db.query(models.ClassInstance)
        .filter(models.ClassInstance.id == instance_id)
        .first()
    )

    if not instance:
        raise HTTPException(status_code=404, detail="Class instance not found")

    # Check if attendance records exist
    attendance_count = (
        db.query(models.FactAttendance)
        .filter(models.FactAttendance.class_instance_id == instance_id)
        .count()
    )

    if attendance_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete class instance: {attendance_count} attendance record(s) are linked to it.",
        )

    db.delete(instance)
    db.commit()

    return {"message": "Class instance deleted successfully"}
