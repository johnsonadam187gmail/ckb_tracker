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
from ..services.cloudinary_service import cloudinary_service

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
    public_id = None
    thumbnail_url = None

    if file:
        try:
            # Generate temporary UUID for the user (will be replaced after creation)
            temp_uuid = str(uuid.uuid4())

            # Read file content - ensure we seek to beginning first
            file.file.seek(0)
            image_bytes = file.file.read()

            # Debug: Check what we received
            print(
                f"DEBUG: Received file: {file.filename}, size: {len(image_bytes)} bytes, type: {file.content_type}"
            )

            if len(image_bytes) == 0:
                raise ValueError("Received empty file")

            # Upload to Cloudinary with temporary UUID
            upload_result = cloudinary_service.upload_profile_photo(
                image_bytes=image_bytes, user_uuid=temp_uuid
            )

            print(f"DEBUG: Upload successful, URL: {upload_result['url']}")

            image_url = upload_result["url"]
            public_id = upload_result["public_id"]
            thumbnail_url = upload_result["thumbnail_url"]

        except ValueError as e:
            raise HTTPException(
                status_code=400, detail=f"Image validation failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload image: {str(e)}"
            )

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

    # If we uploaded an image, we need to re-upload it with the correct UUID
    # This is necessary because we didn't have the user's UUID before creation
    if public_id and image_url:
        try:
            # Extract old public_id and delete it
            old_public_id = cloudinary_service.extract_public_id_from_url(image_url)
            if old_public_id:
                cloudinary_service.delete_photo(old_public_id)

            # Re-upload with correct UUID
            image_bytes = file.file.read() if hasattr(file.file, "read") else None
            if image_bytes:
                upload_result = cloudinary_service.upload_profile_photo(
                    image_bytes=image_bytes, user_uuid=new_user.user_uuid
                )

                # Update the user record with new URLs
                new_user.profile_image_url = upload_result["url"]
                db.commit()
                db.refresh(new_user)
        except Exception:
            # If re-upload fails, keep the original URL - it's still valid
            pass

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

    # 2. Handle image upload if provided
    image_url = old_record.profile_image_url
    old_public_id = None

    if file:
        try:
            # Extract old public_id for deletion
            if old_record.profile_image_url:
                old_public_id = cloudinary_service.extract_public_id_from_url(
                    old_record.profile_image_url
                )

            # Read and upload new image
            image_bytes = file.file.read()
            upload_result = cloudinary_service.upload_profile_photo(
                image_bytes=image_bytes,
                user_uuid=user_uuid,
                old_public_id=old_public_id,
            )

            image_url = upload_result["url"]

        except ValueError as e:
            raise HTTPException(
                status_code=400, detail=f"Image validation failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload image: {str(e)}"
            )

    # 3. EXPIRE the old record
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

    # 4. CREATE the new record
    new_version = models.User(
        user_uuid=user_uuid,
        first_name=first_name,
        last_name=last_name,
        email=email,
        rank=rank,
        nicknames=nicknames,
        password_hash=old_record.password_hash,
        profile_image_url=image_url,
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


@router.post("/{user_uuid}/photo", response_model=schemas.UserPhotoResponse)
def update_user_photo(
    user_uuid: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Update or add a profile photo for an existing user.

    This endpoint allows updating just the photo without modifying other user data.
    Uses SCD Type 2 versioning to maintain history.
    """
    # 1. Find the CURRENT active record for this person
    old_record = (
        db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == True)
        .first()
    )

    if not old_record:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Validate and upload image
    try:
        # Extract old public_id for deletion
        old_public_id = None
        if old_record.profile_image_url:
            old_public_id = cloudinary_service.extract_public_id_from_url(
                old_record.profile_image_url
            )

        # Read and upload new image
        image_bytes = file.file.read()
        upload_result = cloudinary_service.upload_profile_photo(
            image_bytes=image_bytes, user_uuid=user_uuid, old_public_id=old_public_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Image validation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

    # 3. EXPIRE the old record
    now = datetime.now(timezone.utc)
    old_record.is_current = False
    old_record.end_date = now
    old_record.updated_date = now

    # 4. CREATE the new record with updated photo
    new_version = models.User(
        user_uuid=user_uuid,
        first_name=old_record.first_name,
        last_name=old_record.last_name,
        email=old_record.email,
        rank=old_record.rank,
        nicknames=old_record.nicknames,
        password_hash=old_record.password_hash,
        profile_image_url=upload_result["url"],
        last_graded_date=old_record.last_graded_date,
        comments=old_record.comments,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=old_record.created_date,
        updated_date=datetime.now(timezone.utc),
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return {
        "message": "Photo updated successfully",
        "user_uuid": user_uuid,
        "photo_url": upload_result["url"],
        "thumbnail_url": upload_result["thumbnail_url"],
    }


@router.delete("/{user_uuid}/photo", response_model=schemas.UserPhotoResponse)
def delete_user_photo(
    user_uuid: str,
    db: Session = Depends(get_db),
):
    """
    Delete a user's profile photo.

    Uses SCD Type 2 versioning to maintain history.
    """
    # 1. Find the CURRENT active record for this person
    old_record = (
        db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == True)
        .first()
    )

    if not old_record:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Delete photo from Cloudinary if exists
    if old_record.profile_image_url:
        try:
            public_id = cloudinary_service.extract_public_id_from_url(
                old_record.profile_image_url
            )
            if public_id:
                cloudinary_service.delete_photo(public_id)
        except Exception:
            # Continue even if Cloudinary deletion fails
            pass

    # 3. EXPIRE the old record
    now = datetime.now(timezone.utc)
    old_record.is_current = False
    old_record.end_date = now
    old_record.updated_date = now

    # 4. CREATE the new record without photo
    new_version = models.User(
        user_uuid=user_uuid,
        first_name=old_record.first_name,
        last_name=old_record.last_name,
        email=old_record.email,
        rank=old_record.rank,
        nicknames=old_record.nicknames,
        password_hash=old_record.password_hash,
        profile_image_url=None,
        last_graded_date=old_record.last_graded_date,
        comments=old_record.comments,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=old_record.created_date,
        updated_date=datetime.now(timezone.utc),
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return {
        "message": "Photo deleted successfully",
        "user_uuid": user_uuid,
        "photo_url": None,
        "thumbnail_url": None,
    }
