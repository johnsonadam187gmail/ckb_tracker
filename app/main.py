import shutil
from pathlib import Path
from typing import Optional, List
from dateutil import parser
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from . import models, database, schemas

# Import your local modules
from app import models, database, schemas

# Initialize the FastAPI app
app = FastAPI(title="Attendance Tracking System")

# Create the database tables on startup
# Note: In production, you'd use Alembic for migrations, 
# but this is perfect for getting started.
models.Base.metadata.create_all(bind=database.engine)

UPLOAD_DIR = Path("static/profile_pics")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Attendance API is live!"}

# Endpoint to create a new user
@app.post("/users/", response_model=schemas.UserResponse)
def create_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    rank: Optional[str] = Form(None),
    comments: Optional[str] = Form(None),
    nicknames: Optional[str] = Form(None),
    last_graded_date: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None), 
    db: Session = Depends(database.get_db)
):
    # 1. Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Handle the Image logic if a file was actually uploaded
    image_url = None
    if file:
        file_path = UPLOAD_DIR / f"{email}_{file.filename}"
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        image_url = str(file_path)

    # Convert string to date object if it exists
    parsed_date = None
    if last_graded_date:
        try:
            # This converts "2025-12-20" into a real Python date object
            parsed_date = parser.parse(last_graded_date).date()
        except:
            raise HTTPException(status_code=400, detail="Invalid date format")

    # 3. Create the Database Record (The Blueprint)
    new_user = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name=first_name,
        last_name=last_name,
        email=email,
        rank=rank,
        comments=comments,
        nicknames=nicknames,
        last_graded_date=parsed_date,
        profile_image_url=image_url, # This will be the path or None
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
        updated_date=datetime.now(timezone.utc)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Endpoint to fetch all users (for the Analytics UI)
@app.get("/users/", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(database.get_db)):
    return db.query(models.User).all()

app.mount("/static", StaticFiles(directory="static"), name="static")
