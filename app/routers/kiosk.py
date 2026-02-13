from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_password_hash, verify_password
from app.database import get_db

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


def get_current_admin_user(db: Session = Depends(get_db), token: str = None):
    """Dependency to verify admin user (placeholder - implement proper JWT validation)."""
    # This is a simplified version - in production, validate JWT token
    # For now, we'll accept any request and let the Settings page auth handle it
    pass


@router.post("/verify-pin", response_model=schemas.KioskPinVerifyResponse)
def verify_kiosk_pin(
    request: schemas.KioskPinVerifyRequest, db: Session = Depends(get_db)
):
    """Verify the kiosk PIN for student check-in mode.

    Returns success if PIN is valid, 401 if invalid.
    """
    # Get the kiosk auth record (should only be one)
    kiosk_auth = db.query(models.KioskAuth).first()

    if not kiosk_auth:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kiosk PIN not configured. Please contact an administrator.",
        )

    # Verify the PIN
    if not verify_password(request.pin, kiosk_auth.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
        )

    return {"message": "PIN verified successfully", "valid": True}


@router.put("/update-pin", status_code=status.HTTP_200_OK)
def update_kiosk_pin(
    request: schemas.KioskPinUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update the kiosk PIN (requires current PIN for verification).

    This endpoint is typically called from the Settings page where
    admin authentication is already verified.
    """
    # Get the kiosk auth record
    kiosk_auth = db.query(models.KioskAuth).first()

    if not kiosk_auth:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kiosk PIN not configured",
        )

    # Verify current PIN
    if not verify_password(request.current_pin, kiosk_auth.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current PIN is incorrect",
        )

    # Hash and update the new PIN
    new_pin_hash = get_password_hash(request.new_pin)
    kiosk_auth.pin_hash = new_pin_hash

    db.commit()

    return {"message": "PIN updated successfully"}


@router.post("/setup-default-pin", status_code=status.HTTP_201_CREATED)
def setup_default_kiosk_pin(db: Session = Depends(get_db)):
    """Initialize kiosk with default PIN (for first-time setup).

    This should only be called during database seeding or migration.
    Default PIN is '1234' - should be changed immediately after setup.
    """
    # Check if kiosk auth already exists
    existing = db.query(models.KioskAuth).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kiosk PIN already configured",
        )

    # Create default PIN hash (1234)
    default_pin_hash = get_password_hash("1234")

    # Create kiosk auth record
    kiosk_auth = models.KioskAuth(pin_hash=default_pin_hash)
    db.add(kiosk_auth)
    db.commit()

    return {
        "message": "Default kiosk PIN created successfully",
        "warning": "Default PIN is '1234'. Please change immediately for security.",
    }
