from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/teacher/{teacher_uuid}", response_model=List[schemas.FeedbackResponse])
def get_feedback_for_teacher(teacher_uuid: str, db: Session = Depends(get_db)):
    """Gets all feedback for classes taught by a specific teacher (anonymous students)."""
    feedback_query = (
        db.query(
            models.ClassFeedback,
            models.ClassInstance.class_date,
            models.ClassSchedule.class_name,
            models.Lesson.title,
        )
        .join(
            models.ClassInstance,
            models.ClassFeedback.class_instance_id == models.ClassInstance.id,
        )
        .join(
            models.ClassSchedule,
            models.ClassInstance.class_id == models.ClassSchedule.id,
        )
        .outerjoin(models.Lesson, models.ClassInstance.lesson_id == models.Lesson.id)
        .filter(models.ClassInstance.teacher_uuid == teacher_uuid)
        .all()
    )

    # Format response without student names (anonymous)
    results = []
    for fb, class_date, class_name, lesson_title in feedback_query:
        results.append(
            {
                "id": fb.id,
                "user_uuid": fb.user_uuid,
                "attendance_id": fb.attendance_id,
                "class_instance_id": fb.class_instance_id,
                "rating": fb.rating,
                "comment": fb.comment,
                "created_at": fb.created_at,
                "updated_at": fb.updated_at,
                "class_date": class_date,
                "class_name": class_name,
                "lesson_title": lesson_title,
                "user_full_name": None,  # Anonymous for teachers
                "teacher_name": None,
            }
        )

    return results


@router.get(
    "/admin/comprehensive-stats",
    response_model=List[schemas.ComprehensiveFeedbackStats],
)
def get_comprehensive_feedback_stats(db: Session = Depends(get_db)):
    """Gets all feedback with student, teacher, and class details for admin."""
    # Create aliases for User table to avoid conflict
    StudentAlias = aliased(models.User)
    TeacherAlias = aliased(models.User)

    feedback_records = (
        db.query(
            models.ClassFeedback.rating,
            models.ClassFeedback.comment,
            models.ClassInstance.class_date,
            models.ClassSchedule.class_name,
            (StudentAlias.first_name + " " + StudentAlias.last_name).label(
                "student_name"
            ),
            (TeacherAlias.first_name + " " + TeacherAlias.last_name).label(
                "teacher_name"
            ),
        )
        .join(
            models.ClassInstance,
            models.ClassFeedback.class_instance_id == models.ClassInstance.id,
        )
        .join(StudentAlias, models.ClassFeedback.user_uuid == StudentAlias.user_uuid)
        .join(
            models.ClassSchedule,
            models.ClassInstance.class_id == models.ClassSchedule.id,
        )
        .outerjoin(
            TeacherAlias, models.ClassInstance.teacher_uuid == TeacherAlias.user_uuid
        )
        .filter(StudentAlias.is_current == True)
        .all()
    )
    return feedback_records
