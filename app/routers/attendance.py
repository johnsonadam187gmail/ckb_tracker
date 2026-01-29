"""Attendance tracking endpoints."""

from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Form, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/", response_model=schemas.AttendanceResponse)
def record_attendance(
    user_uuid: str = Form(...),
    class_id: int = Form(...),
    attendance_date: str = Form(...),
    db: Session = Depends(get_db),
):
    """Record attendance for a user."""
    date_obj = datetime.strptime(attendance_date, "%Y-%m-%d").date()

    try:
        new_record = models.FactAttendance(
            user_uuid=user_uuid, class_id=class_id, attendance_date=date_obj
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
    query = db.query(models.FactAttendance).join(models.ClassSchedule).join(models.User)

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
    ).all()

    return [
        {
            "id": r.id,
            "attendance_date": r.attendance_date,
            "user_uuid": r.user_uuid,
            "userfullname": f"{r.user.first_name} {r.user.last_name}",
            "rank_at_time": r.user.rank,
            "weighting": r.class_info.weighting,
        }
        for r in records
    ]
