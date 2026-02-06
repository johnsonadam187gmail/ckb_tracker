"""User management endpoints."""

import shutil
from pathlib import Path
from typing import Optional, List
from dateutil import parser
from dateutil.parser import ParserError
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..config import settings
from ..auth import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=schemas.UserResponse)
def create_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    rank: Optional[str] = Form(None),
    comments: Optional[str] = Form(None),
    nicknames: Optional[str] = Form(None),
    last_graded_date: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Create a new user with SCD Type 2 versioning. Password is required."""
    # 1. Check if user already exists
    db_user = (
        db.query(models.User)
        .filter(models.User.email == email, models.User.is_current == True)
        .first()
    )
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Handle the Image logic if a file was actually uploaded
    image_url = None
    if file:
        file_path = settings.upload_dir / f"{email}_{file.filename}"
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        image_url = str(file_path)

    # Convert string to date object if it exists
    parsed_date = None
    if last_graded_date:
        try:
            parsed_date = parser.parse(last_graded_date).date()
        except (ValueError, TypeError, ParserError) as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid date format: {str(e)}"
            )

    # Hash the password
    hashed_password = get_password_hash(password)

    # 3. Create the Database Record
    new_user = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hashed_password,
        rank=rank,
        comments=comments,
        nicknames=nicknames,
        last_graded_date=parsed_date,
        profile_image_url=image_url,
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
        updated_date=datetime.now(timezone.utc),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Assign default "Student" role
    student_role = db.query(models.Role).filter(models.Role.name == "Student").first()
    if student_role:
        user_role = models.UserRole(
            user_uuid=new_user.user_uuid,
            role_id=student_role.id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        db.add(user_role)
        db.commit()

    return new_user


@router.get("/", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(get_db)):
    """Fetch all active users."""
    return db.query(models.User).filter(models.User.is_current == True).all()


@router.put("/{user_uuid}", response_model=schemas.UserResponse)
def update_user(
    user_uuid: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    rank: Optional[str] = Form(None),
    comments: Optional[str] = Form(None),
    nicknames: Optional[str] = Form(None),
    last_graded_date: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Update user using SCD Type 2 pattern."""
    # 1. Find the CURRENT active record for this person
    old_record = (
        db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == True)
        .first()
    )

    if not old_record:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. EXPIRE the old record
    now = datetime.now(timezone.utc)
    old_record.is_current = False
    old_record.end_date = now
    old_record.updated_date = now

    # Parse last_graded_date if provided
    parsed_graded_date = old_record.last_graded_date
    if last_graded_date:
        try:
            parsed_graded_date = parser.parse(last_graded_date).date()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid last_graded_date format. Use YYYY-MM-DD or similar.",
            )

    # 3. CREATE the new record
    new_version = models.User(
        user_uuid=user_uuid,
        first_name=first_name,
        last_name=last_name,
        email=email,
        rank=rank,
        nicknames=nicknames,
        password_hash=old_record.password_hash,
        profile_image_url=old_record.profile_image_url,
        last_graded_date=parsed_graded_date,
        comments=old_record.comments,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=old_record.created_date,
        updated_date=datetime.now(timezone.utc),
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version
