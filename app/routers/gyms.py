"""Gym location management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/gyms", tags=["gyms"])


@router.post("/", response_model=schemas.GymResponse)
def create_gym(gym: schemas.GymCreate, db: Session = Depends(get_db)):
    """Create a new gym location."""
    db_gym = models.GymLocation(**gym.model_dump())
    db.add(db_gym)
    db.commit()
    db.refresh(db_gym)
    return db_gym


@router.get("/", response_model=list[schemas.GymResponse])
def get_gyms(db: Session = Depends(get_db)):
    """Fetch all gym locations."""
    return db.query(models.GymLocation).all()


@router.put("/{gym_id}", response_model=schemas.GymResponse)
def update_gym(gym_id: int, gym_data: schemas.GymCreate, db: Session = Depends(get_db)):
    """Update an existing gym location."""
    db_gym = (
        db.query(models.GymLocation).filter(models.GymLocation.id == gym_id).first()
    )
    if not db_gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    for key, value in gym_data.model_dump().items():
        setattr(db_gym, key, value)
    db.commit()
    db.refresh(db_gym)
    return db_gym
