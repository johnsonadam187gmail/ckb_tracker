"""Attendance tracking endpoints.

Updated: Teacher dashboard now queries via ClassInstance.teacher_uuid.
Updated: Added mat-side workflow support with pending/confirmed status.
"""

from typing import List, Optional
from datetime import datetime, date, timedelta, timezone

from fastapi import APIRouter, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_
from pydantic import BaseModel

from .. import models, schemas
from ..database import get_db
from ..auth import verify_teacher_token, oauth2_scheme

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/", response_model=schemas.AttendanceResponse)
def record_attendance(
    user_uuid: str = Form(...),
    class_id: int = Form(...),
    attendance_date: str = Form(...),
    db: Session = Depends(get_db),
):
    """Record attendance for a user.

    Automatically creates or finds a ClassInstance for the given class and date.
    Teacher assignment is now managed at the ClassInstance level, not per-student.
    """
    date_obj = datetime.strptime(attendance_date, "%Y-%m-%d").date()

    try:
        # Find or create ClassInstance for this class and date
        class_instance = (
            db.query(models.ClassInstance)
            .filter(
                models.ClassInstance.class_id == class_id,
                models.ClassInstance.class_date == date_obj,
            )
            .first()
        )

        if not class_instance:
            # Auto-create ClassInstance if it doesn't exist
            class_instance = models.ClassInstance(
                class_id=class_id,
                class_date=date_obj,
            )
            db.add(class_instance)
            db.flush()  # Get the ID without committing

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
            class_instance_id=class_instance.id,
            attendance_date=date_obj,
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
def get_attendance(
    class_instance_id: Optional[int] = None,
    class_id: Optional[int] = None,
    class_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Fetch all attendance records with optional filtering."""
    query = db.query(models.FactAttendance)

    if class_instance_id:
        query = query.filter(
            models.FactAttendance.class_instance_id == class_instance_id
        )

    if class_id:
        query = query.filter(models.FactAttendance.class_id == class_id)

    if class_date:
        query = query.filter(models.FactAttendance.attendance_date == class_date)

    records = query.all()

    # Enrich with user and class details
    results = []
    for record in records:
        # Get user details
        user = (
            db.query(models.User)
            .filter(
                models.User.user_uuid == record.user_uuid,
                models.User.is_current == True,
            )
            .first()
        )

        # Get class details
        class_info = (
            db.query(models.ClassSchedule)
            .filter(models.ClassSchedule.id == record.class_id)
            .first()
        )

        results.append(
            {
                "id": record.id,
                "attendance_date": record.attendance_date,
                "user_uuid": record.user_uuid,
                "class_id": record.class_id,
                "teacher_uuid": record.teacher_uuid,
                "user_name": f"{user.first_name} {user.last_name}"
                if user
                else "Unknown",
                "class_name": class_info.class_name if class_info else "Unknown",
                "teacher_name": None,  # Could add teacher lookup if needed
                "status": record.status,
                "confirmed_by": record.confirmed_by,
                "confirmed_at": record.confirmed_at,
                "confirmer_name": None,
                "profile_image_url": user.profile_image_url if user else None,
                "first_name": user.first_name if user else "Unknown",
                "last_name": user.last_name if user else "",
                "rank": user.rank if user else "N/A",
                "created_at": record.created_at,
            }
        )

    return results


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
                "points": r.class_info.points,
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
            "points": r.class_info.points,
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
    """Get summary of classes taught by a specific teacher.

    Now queries via ClassInstance.teacher_uuid instead of deprecated
    FactAttendance.teacher_uuid field.
    """
    query = (
        db.query(
            models.ClassInstance.teacher_uuid,
            models.FactAttendance.attendance_date.label("class_date"),
            models.ClassSchedule.class_name,
            func.count(models.FactAttendance.user_uuid).label("student_count"),
            func.sum(models.ClassSchedule.points).label("total_points"),
        )
        .join(
            models.ClassInstance,
            models.FactAttendance.class_instance_id == models.ClassInstance.id,
        )
        .join(
            models.ClassSchedule,
            models.ClassSchedule.id == models.FactAttendance.class_id,
        )
        .filter(models.ClassInstance.teacher_uuid == teacher_uuid)
        .group_by(
            models.ClassInstance.teacher_uuid,
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
    """Update the teacher for an attendance record via its ClassInstance.

    This updates the teacher at the class instance level, affecting all
    students in that class on that date.
    """
    attendance = (
        db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance_id)
        .first()
    )

    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Get the associated class instance
    if not attendance.class_instance_id:
        raise HTTPException(
            status_code=400, detail="Attendance record has no associated class instance"
        )

    class_instance = (
        db.query(models.ClassInstance)
        .filter(models.ClassInstance.id == attendance.class_instance_id)
        .first()
    )

    if not class_instance:
        raise HTTPException(status_code=404, detail="Class instance not found")

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

    # Update teacher at class instance level
    class_instance.teacher_uuid = teacher_data.teacher_uuid
    db.commit()
    db.refresh(class_instance)

    return {
        "message": "Teacher updated successfully for all students in this class",
        "class_instance_id": class_instance.id,
        "teacher_uuid": teacher_data.teacher_uuid,
    }


# ===== MAT-SIDE WORKFLOW ENDPOINTS (Phase 2) =====


@router.post("/check-in", response_model=schemas.AttendanceResponse)
def student_self_check_in(
    request: schemas.StudentCheckInRequest,
    db: Session = Depends(get_db),
):
    """Student self check-in. Creates PENDING attendance record.

    Expires after 6 hours if not confirmed. Idempotent - returns existing
    record if already checked in (pending or confirmed).
    """
    # Check for existing attendance (pending or confirmed)
    existing = (
        db.query(models.FactAttendance)
        .filter(
            models.FactAttendance.user_uuid == request.user_uuid,
            models.FactAttendance.class_id == request.class_id,
            models.FactAttendance.attendance_date == request.attendance_date,
        )
        .first()
    )

    if existing:
        # If already confirmed, return error
        if existing.status == "confirmed":
            raise HTTPException(
                status_code=400,
                detail="You are already checked in and confirmed for this class today.",
            )
        # If pending, return existing record
        return existing

    # Find or create ClassInstance for this class and date
    class_instance = (
        db.query(models.ClassInstance)
        .filter(
            models.ClassInstance.class_id == request.class_id,
            models.ClassInstance.class_date == request.attendance_date,
        )
        .first()
    )

    if not class_instance:
        # Auto-create ClassInstance if it doesn't exist
        class_instance = models.ClassInstance(
            class_id=request.class_id,
            class_date=request.attendance_date,
        )
        db.add(class_instance)
        db.flush()

    # Get user's current Student role for user_role_id
    user_role = (
        db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == request.user_uuid,
            models.UserRole.is_current == True,
            models.Role.name == "Student",
        )
        .first()
    )

    # Create PENDING attendance record
    new_record = models.FactAttendance(
        user_uuid=request.user_uuid,
        class_id=request.class_id,
        class_instance_id=class_instance.id,
        attendance_date=request.attendance_date,
        user_role_id=user_role.id if user_role else None,
        status="pending",
        confirmed_by=None,
        confirmed_at=None,
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record


@router.get(
    "/pending/{class_id}/{class_date}",
    response_model=List[schemas.PendingAttendanceResponse],
)
def get_pending_check_ins(
    class_id: int,
    class_date: date,
    db: Session = Depends(get_db),
):
    """Get all pending check-ins for a specific class and date.

    Used by teacher dashboard to see who needs to be confirmed.
    """
    pending_records = (
        db.query(
            models.FactAttendance.id,
            models.FactAttendance.user_uuid,
            models.FactAttendance.class_id,
            models.FactAttendance.attendance_date,
            models.FactAttendance.created_at,
            models.FactAttendance.status,
            models.User.first_name,
            models.User.last_name,
            models.User.profile_image_url,
            models.ClassSchedule.class_name,
        )
        .join(models.User, models.FactAttendance.user_uuid == models.User.user_uuid)
        .join(
            models.ClassSchedule,
            models.FactAttendance.class_id == models.ClassSchedule.id,
        )
        .filter(
            models.FactAttendance.class_id == class_id,
            models.FactAttendance.attendance_date == class_date,
            models.FactAttendance.status == "pending",
            models.User.is_current == True,
        )
        .order_by(models.FactAttendance.created_at.asc())
        .all()
    )

    results = []
    for r in pending_records:
        results.append(
            {
                "id": r.id,
                "user_uuid": r.user_uuid,
                "student_name": f"{r.first_name} {r.last_name}",
                "class_id": r.class_id,
                "class_name": r.class_name,
                "attendance_date": r.attendance_date,
                "created_at": r.created_at,
                "profile_image_url": r.profile_image_url,
                "status": r.status,
            }
        )

    return results


@router.post("/{attendance_id}/confirm", response_model=schemas.AttendanceResponse)
def confirm_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Teacher confirms a pending attendance record.

    Changes status from 'pending' to 'confirmed'. Requires teacher JWT token.
    """
    # Verify teacher token
    payload = verify_teacher_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    teacher_uuid = payload.get("sub")

    # Get attendance record
    attendance = (
        db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance_id)
        .first()
    )

    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    if attendance.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Attendance is already {attendance.status}",
        )

    # Update to confirmed
    attendance.status = "confirmed"
    attendance.confirmed_by = teacher_uuid
    attendance.confirmed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(attendance)

    return attendance


@router.delete("/{attendance_id}/cancel")
def cancel_own_check_in(
    attendance_id: int,
    user_uuid: str,
    db: Session = Depends(get_db),
):
    """Student cancels their own pending check-in.

    Only allowed if status is 'pending'. Students can only cancel their own records.
    """
    attendance = (
        db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance_id)
        .first()
    )

    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Verify student is canceling their own record
    if attendance.user_uuid != user_uuid:
        raise HTTPException(
            status_code=403,
            detail="You can only cancel your own check-in",
        )

    # Only allow canceling pending records
    if attendance.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel attendance with status: {attendance.status}",
        )

    # Delete the pending record
    db.delete(attendance)
    db.commit()

    return {
        "message": "Check-in cancelled successfully",
        "attendance_id": attendance_id,
    }


@router.post("/direct", response_model=schemas.AttendanceResponse)
def create_direct_attendance(
    request: schemas.DirectAttendanceRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Teacher adds student directly (bypasses self check-in).

    Creates CONFIRMED attendance immediately. Requires teacher JWT token.
    """
    # Verify teacher token
    payload = verify_teacher_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    teacher_uuid = payload.get("sub")

    # Check if attendance already exists
    existing = (
        db.query(models.FactAttendance)
        .filter(
            models.FactAttendance.user_uuid == request.user_uuid,
            models.FactAttendance.class_id == request.class_id,
            models.FactAttendance.attendance_date == request.attendance_date,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Student is already checked in for this class today.",
        )

    # Find or create ClassInstance
    class_instance = (
        db.query(models.ClassInstance)
        .filter(
            models.ClassInstance.class_id == request.class_id,
            models.ClassInstance.class_date == request.attendance_date,
        )
        .first()
    )

    if not class_instance:
        class_instance = models.ClassInstance(
            class_id=request.class_id,
            class_date=request.attendance_date,
        )
        db.add(class_instance)
        db.flush()

    # Get user's Student role
    user_role = (
        db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == request.user_uuid,
            models.UserRole.is_current == True,
            models.Role.name == "Student",
        )
        .first()
    )

    # Create CONFIRMED attendance immediately
    new_record = models.FactAttendance(
        user_uuid=request.user_uuid,
        class_id=request.class_id,
        class_instance_id=class_instance.id,
        attendance_date=request.attendance_date,
        user_role_id=user_role.id if user_role else None,
        status="confirmed",
        confirmed_by=teacher_uuid,
        confirmed_at=datetime.now(timezone.utc),
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record


@router.post("/bulk-confirm", response_model=List[schemas.AttendanceResponse])
def bulk_confirm_attendance(
    request: schemas.BulkConfirmRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Confirm multiple attendance records at once.

    Requires teacher JWT token. Only confirms pending records.
    """
    # Verify teacher token
    payload = verify_teacher_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    teacher_uuid = payload.get("sub")

    # Get all pending records that match the IDs
    records = (
        db.query(models.FactAttendance)
        .filter(
            models.FactAttendance.id.in_(request.attendance_ids),
            models.FactAttendance.status == "pending",
        )
        .all()
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No pending attendance records found for the provided IDs",
        )

    # Update all records
    confirmed_count = 0
    for record in records:
        record.status = "confirmed"
        record.confirmed_by = teacher_uuid
        record.confirmed_at = datetime.now(timezone.utc)
        confirmed_count += 1

    db.commit()

    # Refresh all records
    for record in records:
        db.refresh(record)

    return records


@router.post("/expire-old")
def expire_old_pending_records(db: Session = Depends(get_db)):
    """Delete pending check-ins older than 6 hours.

    This endpoint is designed to be called by a cron job every hour.
    No authentication required - assumes it's called from internal network.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=6)

    # Find and delete old pending records
    old_records = (
        db.query(models.FactAttendance)
        .filter(
            models.FactAttendance.status == "pending",
            models.FactAttendance.created_at < cutoff_time,
        )
        .all()
    )

    deleted_count = len(old_records)

    for record in old_records:
        db.delete(record)

    db.commit()

    return {
        "message": f"Expired {deleted_count} old pending check-ins",
        "deleted_count": deleted_count,
        "cutoff_time": cutoff_time.isoformat(),
    }
