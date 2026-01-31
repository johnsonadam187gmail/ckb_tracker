"""Attendance tracking endpoints."""

from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Form, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from pydantic import BaseModel

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/", response_model=schemas.AttendanceResponse)
def record_attendance(
    user_uuid: str = Form(...),
    class_id: int = Form(...),
    attendance_date: str = Form(...),
    teacher_uuid: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Record attendance for a user, optionally with teacher assignment."""
    date_obj = datetime.strptime(attendance_date, "%Y-%m-%d").date()

    try:
        # Get user's current Student role for user_role_id
        user_role = (
            db.query(models.UserRole)
            .join(models.Role)
            .filter(
                models.UserRole.user_uuid == user_uuid,
                models.UserRole.is_current == True,
                models.Role.name == "Student",
            )
            .first()
        )

        new_record = models.FactAttendance(
            user_uuid=user_uuid,
            class_id=class_id,
            attendance_date=date_obj,
            teacher_uuid=teacher_uuid,
            user_role_id=user_role.id if user_role else None,
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="User is already checked into this class for today."
        )


@router.get("/", response_model=List[schemas.AttendanceResponse])
def get_attendance(db: Session = Depends(get_db)):
    """Fetch all attendance records."""
    return db.query(models.FactAttendance).all()


@router.get("/user/{user_uuid}", response_model=List[schemas.UserAnalyticsResponse])
def get_attendance_by_user(user_uuid: str, db: Session = Depends(get_db)):
    """Get attendance records for a specific user."""
    records = (
        db.query(models.FactAttendance)
        .options(
            joinedload(models.FactAttendance.user),
            joinedload(models.FactAttendance.class_info),
            joinedload(models.FactAttendance.teacher),
        )
        .filter(models.FactAttendance.user_uuid == user_uuid)
        .all()
    )

    results = []
    for r in records:
        results.append(
            {
                "userfullname": f"{r.user.first_name} {r.user.last_name}",
                "id": r.id,
                "attendance_date": r.attendance_date,
                "user_uuid": r.user_uuid,
                "class_name": r.class_info.class_name,
                "weighting": r.class_info.weighting,
                "rank_at_time": r.user.rank,
                "teacher_uuid": r.teacher_uuid,
                "teacher_name": f"{r.teacher.first_name} {r.teacher.last_name}"
                if r.teacher
                else None,
            }
        )

    return results


@router.get("/class/{class_name}", response_model=list[schemas.ClassAttendanceResponse])
def get_class_attendance_detail(
    class_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    rank_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get attendance details for a specific class with optional filters."""
    query = (
        db.query(models.FactAttendance)
        .join(models.ClassSchedule)
        .join(models.User, models.FactAttendance.user_uuid == models.User.user_uuid)
    )

    query = query.filter(models.ClassSchedule.class_name == class_name)

    if start_date:
        query = query.filter(models.FactAttendance.attendance_date >= start_date)
    if end_date:
        query = query.filter(models.FactAttendance.attendance_date <= end_date)
    if rank_filter:
        query = query.filter(models.User.rank == rank_filter)

    records = query.options(
        joinedload(models.FactAttendance.user),
        joinedload(models.FactAttendance.class_info),
        joinedload(models.FactAttendance.teacher),
    ).all()

    return [
        {
            "id": r.id,
            "attendance_date": r.attendance_date,
            "user_uuid": r.user_uuid,
            "userfullname": f"{r.user.first_name} {r.user.last_name}",
            "rank_at_time": r.user.rank,
            "weighting": r.class_info.weighting,
            "teacher_uuid": r.teacher_uuid,
            "teacher_name": f"{r.teacher.first_name} {r.teacher.last_name}"
            if r.teacher
            else None,
        }
        for r in records
    ]


@router.get(
    "/teacher/{teacher_uuid}/classes",
    response_model=List[schemas.TeacherAnalyticsResponse],
)
def get_teacher_class_summary(
    teacher_uuid: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Get summary of classes taught by a specific teacher."""
    query = (
        db.query(
            models.FactAttendance.teacher_uuid,
            models.FactAttendance.attendance_date.label("class_date"),
            models.ClassSchedule.class_name,
            func.count(models.FactAttendance.user_uuid).label("student_count"),
            func.sum(models.ClassSchedule.weighting).label("total_weighting"),
        )
        .join(models.ClassSchedule)
        .filter(models.FactAttendance.teacher_uuid == teacher_uuid)
        .group_by(
            models.FactAttendance.teacher_uuid,
            models.FactAttendance.attendance_date,
            models.ClassSchedule.class_name,
        )
    )

    if start_date:
        query = query.filter(models.FactAttendance.attendance_date >= start_date)
    if end_date:
        query = query.filter(models.FactAttendance.attendance_date <= end_date)

    results = query.all()

    teacher = (
        db.query(models.User)
        .filter(models.User.user_uuid == teacher_uuid, models.User.is_current == True)
        .first()
    )

    teacher_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "Unknown"

    return [
        {
            "teacher_uuid": teacher_uuid,
            "teacher_name": teacher_name,
            "class_name": r.class_name,
            "class_date": r.class_date,
            "student_count": r.student_count,
            "total_weighting": r.total_weighting or 0.0,
        }
        for r in results
    ]


class TeacherUpdate(BaseModel):
    teacher_uuid: str


@router.put("/{attendance_id}/teacher")
def update_attendance_teacher(
    attendance_id: int, teacher_data: TeacherUpdate, db: Session = Depends(get_db)
):
    """Update the teacher for a specific attendance record."""
    attendance = (
        db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance_id)
        .first()
    )

    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Verify teacher exists and has Teacher role
    teacher = (
        db.query(models.User)
        .filter(
            models.User.user_uuid == teacher_data.teacher_uuid,
            models.User.is_current == True,
        )
        .first()
    )

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Verify teacher has Teacher role
    teacher_role = (
        db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == teacher_data.teacher_uuid,
            models.UserRole.is_current == True,
            models.Role.name == "Teacher",
        )
        .first()
    )

    if not teacher_role:
        raise HTTPException(
            status_code=400,
            detail=f"User {teacher.first_name} {teacher.last_name} does not have Teacher role",
        )

    # Update teacher
    attendance.teacher_uuid = teacher_data.teacher_uuid
    db.commit()
    db.refresh(attendance)

    return {
        "message": "Teacher updated successfully",
        "attendance_id": attendance_id,
        "teacher_uuid": teacher_data.teacher_uuid,
    }
