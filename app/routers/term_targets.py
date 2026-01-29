"""Term target management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/term-targets", tags=["term-targets"])


@router.post("/", response_model=schemas.TermTargetResponse)
def set_term_target(
    target_data: schemas.TermTargetCreate, db: Session = Depends(get_db)
):
    """Create or update a term target (upsert pattern)."""
    existing_target = (
        db.query(models.TermTarget)
        .filter(
            models.TermTarget.term_id == target_data.term_id,
            models.TermTarget.rank == target_data.rank,
        )
        .first()
    )

    if existing_target:
        existing_target.target = target_data.target
        db.commit()
        db.refresh(existing_target)
        return existing_target

    db_target = models.TermTarget(**target_data.model_dump())
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return db_target


@router.get("/", response_model=list[schemas.TermTargetResponse])
def get_all_term_targets(db: Session = Depends(get_db)):
    """Fetch all term targets."""
    return db.query(models.TermTarget).all()


@router.get("/term/{term_id}", response_model=list[schemas.TermTargetResponse])
def get_targets_by_term(term_id: int, db: Session = Depends(get_db)):
    """Fetch targets for a specific term."""
    targets = (
        db.query(models.TermTarget).filter(models.TermTarget.term_id == term_id).all()
    )
    if not targets:
        return []
    return targets


@router.put("/{target_id}", response_model=schemas.TermTargetResponse)
def update_term_target(
    target_id: int, target_data: schemas.TermTargetUpdate, db: Session = Depends(get_db)
):
    """Update a specific term target."""
    db_target = (
        db.query(models.TermTarget).filter(models.TermTarget.id == target_id).first()
    )

    if not db_target:
        raise HTTPException(status_code=404, detail="Target not found")

    db_target.target = target_data.target
    db.commit()
    db.refresh(db_target)
    return db_target
