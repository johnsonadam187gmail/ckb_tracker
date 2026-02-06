from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import IntegrityError
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post(
    "/", response_model=schemas.FeedbackResponse, status_code=status.HTTP_201_CREATED
)
def create_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    """Creates new feedback for a class attendance."""

    # 1. Get the attendance record
    attendance = (
        db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == feedback.attendance_id)
        .first()
    )

    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found"
        )

    # 2. Check if class_instance exists
    if not attendance.class_instance_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This attendance record is not linked to a class instance",
        )

    # 3. Check if feedback already exists for this attendance
    existing_feedback = (
        db.query(models.ClassFeedback)
        .filter(models.ClassFeedback.attendance_id == feedback.attendance_id)
        .first()
    )

    if existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback already submitted for this attendance",
        )

    # 4. Create new feedback
    new_feedback = models.ClassFeedback(
        user_uuid=attendance.user_uuid,
        attendance_id=feedback.attendance_id,
        class_instance_id=attendance.class_instance_id,
        rating=feedback.rating,
        comment=feedback.comment,
    )

    try:
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create feedback due to data integrity issue",
        )

    # 5. Return the created feedback with additional info
    class_instance = (
        db.query(models.ClassInstance)
        .filter(models.ClassInstance.id == new_feedback.class_instance_id)
        .first()
    )

    class_schedule = None
    lesson_title = None

    if class_instance:
        class_schedule = (
            db.query(models.ClassSchedule)
            .filter(models.ClassSchedule.id == class_instance.class_id)
            .first()
        )

        if class_instance.lesson_id:
            lesson = (
                db.query(models.Lesson)
                .filter(models.Lesson.id == class_instance.lesson_id)
                .first()
            )
            lesson_title = lesson.title if lesson else None

    return {
        "id": new_feedback.id,
        "user_uuid": new_feedback.user_uuid,
        "attendance_id": new_feedback.attendance_id,
        "class_instance_id": new_feedback.class_instance_id,
        "rating": new_feedback.rating,
        "comment": new_feedback.comment,
        "created_at": new_feedback.created_at,
        "updated_at": new_feedback.updated_at,
        "class_date": class_instance.class_date if class_instance else None,
        "class_name": class_schedule.class_name if class_schedule else None,
        "lesson_title": lesson_title,
        "user_full_name": None,
        "teacher_name": None,
    }


@router.get("/user/{user_uuid}", response_model=List[schemas.FeedbackResponse])
def get_feedback_for_user(user_uuid: str, db: Session = Depends(get_db)):
    """Gets all feedback submitted by a specific user (for Student Portal)."""
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
        .filter(models.ClassFeedback.user_uuid == user_uuid)
        .all()
    )

    # Format response
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
                "user_full_name": None,
                "teacher_name": None,
            }
        )

    return results


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
