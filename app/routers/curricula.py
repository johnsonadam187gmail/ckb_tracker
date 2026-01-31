"""Curriculum management endpoints."""

from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/curricula", tags=["curricula"])


@router.post("/", response_model=schemas.CurriculumResponse)
def create_curriculum(
    curriculum_data: schemas.CurriculumCreate, db: Session = Depends(get_db)
):
    """Create a curriculum for a class.

    Each class can only have one curriculum (1:1 relationship).
    If name is not provided, it will be auto-generated from class name.
    """
    # Check if class exists
    class_schedule = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.id == curriculum_data.class_id)
        .first()
    )

    if not class_schedule:
        raise HTTPException(status_code=404, detail="Class not found")

    # Check if curriculum already exists for this class
    existing = (
        db.query(models.Curriculum)
        .filter(models.Curriculum.class_id == curriculum_data.class_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Curriculum already exists for class '{class_schedule.class_name}'",
        )

    # Auto-generate name if not provided
    curriculum_name = curriculum_data.name
    if not curriculum_name:
        curriculum_name = f"{class_schedule.class_name} Curriculum"

    # Create curriculum
    db_curriculum = models.Curriculum(
        class_id=curriculum_data.class_id,
        name=curriculum_name,
        description=curriculum_data.description,
    )

    try:
        db.add(db_curriculum)
        db.commit()
        db.refresh(db_curriculum)
        return db_curriculum
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Failed to create curriculum (integrity constraint)",
        )


@router.get("/", response_model=List[schemas.CurriculumResponse])
def get_curricula(db: Session = Depends(get_db)):
    """Get all curricula."""
    curricula = db.query(models.Curriculum).all()
    return curricula


@router.get("/{curriculum_id}", response_model=schemas.CurriculumResponse)
def get_curriculum(curriculum_id: int, db: Session = Depends(get_db)):
    """Get a specific curriculum by ID."""
    curriculum = (
        db.query(models.Curriculum)
        .filter(models.Curriculum.id == curriculum_id)
        .first()
    )

    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")

    return curriculum


@router.get("/by-class/{class_id}", response_model=schemas.CurriculumResponse)
def get_curriculum_by_class(class_id: int, db: Session = Depends(get_db)):
    """Get curriculum for a specific class."""
    curriculum = (
        db.query(models.Curriculum)
        .filter(models.Curriculum.class_id == class_id)
        .first()
    )

    if not curriculum:
        raise HTTPException(
            status_code=404,
            detail=f"No curriculum found for class ID {class_id}",
        )

    return curriculum


@router.put("/{curriculum_id}", response_model=schemas.CurriculumResponse)
def update_curriculum(
    curriculum_id: int,
    update_data: schemas.CurriculumUpdate,
    db: Session = Depends(get_db),
):
    """Update a curriculum."""
    curriculum = (
        db.query(models.Curriculum)
        .filter(models.Curriculum.id == curriculum_id)
        .first()
    )

    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(curriculum, key, value)

    curriculum.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(curriculum)
    return curriculum


@router.delete("/{curriculum_id}")
def delete_curriculum(curriculum_id: int, db: Session = Depends(get_db)):
    """Delete a curriculum.

    This will cascade delete all lessons in the curriculum.
    Will fail if any class instances reference lessons from this curriculum.
    """
    curriculum = (
        db.query(models.Curriculum)
        .filter(models.Curriculum.id == curriculum_id)
        .first()
    )

    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")

    # Check if any lessons from this curriculum are assigned to class instances
    lesson_ids = [lesson.id for lesson in curriculum.lessons]
    if lesson_ids:
        assigned_count = (
            db.query(models.ClassInstance)
            .filter(models.ClassInstance.lesson_id.in_(lesson_ids))
            .count()
        )

        if assigned_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete curriculum: {assigned_count} lesson(s) are assigned to class instances",
            )

    db.delete(curriculum)
    db.commit()

    return {"message": "Curriculum deleted successfully"}
