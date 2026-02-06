from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import (
    create_teacher_token,
    extend_teacher_token,
    get_password_hash,
    verify_password,
    verify_teacher_token,
)
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/teacher-login", response_model=schemas.TeacherLoginResponse)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Handles teacher login and returns a JWT."""
    user = (
        db.query(models.User)
        .filter(models.User.email == form_data.username, models.User.is_current == True)
        .first()
    )

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if the user has the 'Teacher' role
    teacher_role = db.query(models.Role).filter(models.Role.name == "Teacher").first()
    if not teacher_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Teacher role not found",
        )

    user_role = (
        db.query(models.UserRole)
        .filter(
            models.UserRole.user_uuid == user.user_uuid,
            models.UserRole.role_id == teacher_role.id,
            models.UserRole.is_current == True,
        )
        .first()
    )

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    access_token = create_teacher_token(data={"sub": user.user_uuid})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": schemas.UserResponse.from_orm(user),
    }


@router.post("/verify-session", response_model=schemas.SessionVerifyResponse)
def verify_session(request: schemas.SessionVerifyRequest):
    """Verifies a teacher's session token and returns a new one."""
    token = request.token
    payload = verify_teacher_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    # Extend the token's expiration
    new_token = extend_teacher_token(token)
    return {"status": "ok", "new_token": new_token, "user_uuid": payload.get("sub")}


@router.post("/login", response_model=schemas.UserResponse)
def student_login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Handles student login and returns user info (no role restrictions)."""
    user = (
        db.query(models.User)
        .filter(models.User.email == request.email, models.User.is_current == True)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user has a password set
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No password set. Please contact your instructor to set up a password.",
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Return user info (no JWT token for students, they use session state in frontend)
    return schemas.UserResponse.from_orm(user)


@router.post("/set-password", status_code=status.HTTP_200_OK)
def set_password(request: schemas.SetPasswordRequest, db: Session = Depends(get_db)):
    """Sets or updates a user's password."""
    # Find the current user record
    user = (
        db.query(models.User)
        .filter(
            models.User.user_uuid == request.user_uuid,
            models.User.is_current == True,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Hash the new password
    hashed_password = get_password_hash(request.password)

    # Update the user's password
    user.password_hash = hashed_password
    db.commit()

    return {"message": "Password set successfully", "user_uuid": request.user_uuid}


@router.get("/check-password/{user_uuid}")
def check_password(user_uuid: str, db: Session = Depends(get_db)):
    """Checks if a user has a password set."""
    user = (
        db.query(models.User)
        .filter(
            models.User.user_uuid == user_uuid,
            models.User.is_current == True,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    has_password = user.password_hash is not None and user.password_hash != ""

    return {"user_uuid": user_uuid, "has_password": has_password}


@router.delete("/remove-password/{user_uuid}", status_code=status.HTTP_200_OK)
def remove_password(user_uuid: str, db: Session = Depends(get_db)):
    """Removes a user's password."""
    user = (
        db.query(models.User)
        .filter(
            models.User.user_uuid == user_uuid,
            models.User.is_current == True,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Set password_hash to None
    user.password_hash = None
    db.commit()

    return {"message": "Password removed successfully", "user_uuid": user_uuid}
