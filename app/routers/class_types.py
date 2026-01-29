"""Class type management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/class-types", tags=["class-types"])


@router.post("/", response_model=schemas.ClassTypeResponse)
def create_class_type(ctype: schemas.ClassTypeCreate, db: Session = Depends(get_db)):
    """Create a new class type."""
    db_type = models.ClassType(**ctype.model_dump())
    db.add(db_type)
    db.commit()
    db.refresh(db_type)
    return db_type


@router.get("/", response_model=list[schemas.ClassTypeResponse])
def get_class_types(db: Session = Depends(get_db)):
    """Fetch all class types."""
    return db.query(models.ClassType).all()
