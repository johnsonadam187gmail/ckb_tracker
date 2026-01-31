"""Lesson management endpoints."""

from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.post("/", response_model=schemas.LessonResponse)
def create_lesson(lesson_data: schemas.LessonCreate, db: Session = Depends(get_db)):
    """Create a lesson in a curriculum."""
    # Verify curriculum exists
    curriculum = (
        db.query(models.Curriculum)
        .filter(models.Curriculum.id == lesson_data.curriculum_id)
        .first()
    )

    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")

    # Create lesson - convert HttpUrl to string
    lesson_dict = lesson_data.model_dump()
    if lesson_dict.get("lesson_plan_url"):
        lesson_dict["lesson_plan_url"] = str(lesson_dict["lesson_plan_url"])
    if lesson_dict.get("video_folder_url"):
        lesson_dict["video_folder_url"] = str(lesson_dict["video_folder_url"])

    db_lesson = models.Lesson(**lesson_dict)

    try:
        db.add(db_lesson)
        db.commit()
        db.refresh(db_lesson)
        return db_lesson
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create lesson: {str(e)}",
        )


@router.get("/", response_model=List[schemas.LessonResponse])
def get_lessons(
    curriculum_id: Optional[int] = Query(None), db: Session = Depends(get_db)
):
    """Get all lessons, optionally filtered by curriculum."""
    query = db.query(models.Lesson)

    if curriculum_id:
        query = query.filter(models.Lesson.curriculum_id == curriculum_id)

    lessons = query.order_by(models.Lesson.created_at).all()
    return lessons


@router.get("/{lesson_id}", response_model=schemas.LessonResponse)
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """Get a specific lesson by ID."""
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return lesson


@router.put("/{lesson_id}", response_model=schemas.LessonResponse)
def update_lesson(
    lesson_id: int,
    update_data: schemas.LessonUpdate,
    db: Session = Depends(get_db),
):
    """Update a lesson."""
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Update fields - convert HttpUrl to string
    update_dict = update_data.model_dump(exclude_unset=True)
    if "lesson_plan_url" in update_dict and update_dict["lesson_plan_url"]:
        update_dict["lesson_plan_url"] = str(update_dict["lesson_plan_url"])
    if "video_folder_url" in update_dict and update_dict["video_folder_url"]:
        update_dict["video_folder_url"] = str(update_dict["video_folder_url"])

    for key, value in update_dict.items():
        setattr(lesson, key, value)

    lesson.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """Delete a lesson.

    Will fail if the lesson is assigned to any class instances.
    """
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Check if lesson is assigned to any class instances
    assigned_count = (
        db.query(models.ClassInstance)
        .filter(models.ClassInstance.lesson_id == lesson_id)
        .count()
    )

    if assigned_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete lesson: assigned to {assigned_count} class instance(s)",
        )

    db.delete(lesson)
    db.commit()

    return {"message": "Lesson deleted successfully"}
