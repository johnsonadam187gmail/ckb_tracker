"""Term management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/terms", tags=["terms"])


@router.post("/", response_model=schemas.TermResponse)
def create_term(term: schemas.TermCreate, db: Session = Depends(get_db)):
    """Create a new term with overlap validation."""
    overlap = (
        db.query(models.Term)
        .filter(
            models.Term.start_date <= term.end_date,
            models.Term.end_date >= term.start_date,
        )
        .first()
    )

    if overlap:
        raise HTTPException(
            status_code=400,
            detail=f"Term dates overlap with existing term: {overlap.term_name}",
        )

    db_term = models.Term(**term.model_dump())
    db.add(db_term)
    db.commit()
    db.refresh(db_term)
    return db_term


@router.get("/", response_model=list[schemas.TermResponse])
def get_terms(db: Session = Depends(get_db)):
    """Fetch all terms."""
    return db.query(models.Term).order_by(models.Term.start_date.desc()).all()


@router.put("/{term_id}", response_model=schemas.TermResponse)
def update_term(
    term_id: int, term_data: schemas.TermUpdate, db: Session = Depends(get_db)
):
    """Update an existing term."""
    db_term = db.query(models.Term).filter(models.Term.id == term_id).first()
    if not db_term:
        raise HTTPException(status_code=404, detail="Term not found")

    update_dict = term_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_term, key, value)

    db.commit()
    db.refresh(db_term)
    return db_term
