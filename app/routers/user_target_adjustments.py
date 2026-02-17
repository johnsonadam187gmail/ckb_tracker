"""User target adjustment endpoints for manual point management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/user-target-adjustments", tags=["user-target-adjustments"])


@router.post("/", response_model=schemas.UserTargetAdjustmentResponse)
def create_adjustment(
    adjustment_data: schemas.UserTargetAdjustmentCreate,
    admin_name: Optional[str] = Query(None, description="Admin username for tracking"),
    db: Session = Depends(get_db),
):
    """Create or update a target adjustment for a user in a specific term.

    If an adjustment already exists for this user/term combination, it will be updated.
    """
    # Check if user exists
    user = (
        db.query(models.User)
        .filter(
            models.User.user_uuid == adjustment_data.user_uuid,
            models.User.is_current == True,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if term exists
    term = (
        db.query(models.Term).filter(models.Term.id == adjustment_data.term_id).first()
    )
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    # Check if adjustment already exists for this user/term
    existing = (
        db.query(models.UserTargetAdjustment)
        .filter(
            models.UserTargetAdjustment.user_uuid == adjustment_data.user_uuid,
            models.UserTargetAdjustment.term_id == adjustment_data.term_id,
        )
        .first()
    )

    if existing:
        # Update existing adjustment
        existing.adjustment = adjustment_data.adjustment
        existing.reason = adjustment_data.reason
        db.commit()
        db.refresh(existing)
        return existing

    # Create new adjustment
    db_adjustment = models.UserTargetAdjustment(
        **adjustment_data.model_dump(), created_by=admin_name
    )
    db.add(db_adjustment)
    db.commit()
    db.refresh(db_adjustment)
    return db_adjustment


@router.get("/", response_model=list[schemas.UserTargetAdjustmentResponse])
def get_all_adjustments(
    term_id: Optional[int] = Query(None, description="Filter by term ID"),
    user_uuid: Optional[str] = Query(None, description="Filter by user UUID"),
    db: Session = Depends(get_db),
):
    """Fetch all target adjustments with optional filtering."""
    query = db.query(models.UserTargetAdjustment)

    if term_id:
        query = query.filter(models.UserTargetAdjustment.term_id == term_id)
    if user_uuid:
        query = query.filter(models.UserTargetAdjustment.user_uuid == user_uuid)

    return query.all()


@router.get(
    "/user/{user_uuid}/term/{term_id}",
    response_model=schemas.UserTargetAdjustmentResponse,
)
def get_user_term_adjustment(
    user_uuid: str,
    term_id: int,
    db: Session = Depends(get_db),
):
    """Get adjustment for a specific user in a specific term."""
    adjustment = (
        db.query(models.UserTargetAdjustment)
        .filter(
            models.UserTargetAdjustment.user_uuid == user_uuid,
            models.UserTargetAdjustment.term_id == term_id,
        )
        .first()
    )

    if not adjustment:
        raise HTTPException(
            status_code=404, detail="No adjustment found for this user/term"
        )

    return adjustment


@router.get("/summary", response_model=dict)
def get_adjustments_summary(
    term_id: Optional[int] = Query(None, description="Filter by term ID"),
    db: Session = Depends(get_db),
):
    """Get summary statistics of adjustments."""
    query = db.query(models.UserTargetAdjustment)

    if term_id:
        query = query.filter(models.UserTargetAdjustment.term_id == term_id)

    adjustments = query.all()

    total_adjustments = len(adjustments)
    total_positive = sum(1 for a in adjustments if a.adjustment > 0)
    total_negative = sum(1 for a in adjustments if a.adjustment < 0)
    sum_adjustments = sum(a.adjustment for a in adjustments)

    return {
        "total_adjustments": total_adjustments,
        "total_positive": total_positive,
        "total_negative": total_negative,
        "sum_adjustments": sum_adjustments,
    }


@router.put("/{adjustment_id}", response_model=schemas.UserTargetAdjustmentResponse)
def update_adjustment(
    adjustment_id: int,
    adjustment_data: schemas.UserTargetAdjustmentUpdate,
    db: Session = Depends(get_db),
):
    """Update a specific adjustment."""
    db_adjustment = (
        db.query(models.UserTargetAdjustment)
        .filter(models.UserTargetAdjustment.id == adjustment_id)
        .first()
    )

    if not db_adjustment:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    db_adjustment.adjustment = adjustment_data.adjustment
    db_adjustment.reason = adjustment_data.reason
    db.commit()
    db.refresh(db_adjustment)
    return db_adjustment


@router.delete("/{adjustment_id}")
def delete_adjustment(adjustment_id: int, db: Session = Depends(get_db)):
    """Delete a specific adjustment."""
    db_adjustment = (
        db.query(models.UserTargetAdjustment)
        .filter(models.UserTargetAdjustment.id == adjustment_id)
        .first()
    )

    if not db_adjustment:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    db.delete(db_adjustment)
    db.commit()
    return {"message": "Adjustment deleted successfully"}


@router.get("/user/{user_uuid}/effective-target", response_model=dict)
def get_user_effective_target(
    user_uuid: str,
    term_id: int,
    db: Session = Depends(get_db),
):
    """Get the effective target for a user in a term (base target + adjustment)."""
    # Get user
    user = (
        db.query(models.User)
        .filter(
            models.User.user_uuid == user_uuid,
            models.User.is_current == True,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get base target from term_targets based on user's rank
    base_target = 0.0
    if user.rank:
        term_target = (
            db.query(models.TermTarget)
            .filter(
                models.TermTarget.term_id == term_id,
                models.TermTarget.rank == user.rank,
            )
            .first()
        )
        if term_target:
            base_target = term_target.target

    # Get adjustment
    adjustment = (
        db.query(models.UserTargetAdjustment)
        .filter(
            models.UserTargetAdjustment.user_uuid == user_uuid,
            models.UserTargetAdjustment.term_id == term_id,
        )
        .first()
    )
    adjustment_value = adjustment.adjustment if adjustment else 0.0

    return {
        "user_uuid": user_uuid,
        "term_id": term_id,
        "user_name": f"{user.first_name} {user.last_name}",
        "user_rank": user.rank,
        "base_target": base_target,
        "adjustment": adjustment_value,
        "effective_target": base_target + adjustment_value,
    }
