import shutil
from pathlib import Path
from typing import Optional, List
from dateutil import parser
import uuid
from datetime import datetime, timezone, date
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
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
    db_user = db.query(models.User).filter(models.User.email == email,models.User.is_current == True).first()
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

@app.put("/users/{user_uuid}", response_model=schemas.UserResponse)
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
    db: Session = Depends(database.get_db)
):
    # 1. Find the CURRENT active record for this person
    old_record = db.query(models.User).filter(
        models.User.user_uuid == user_uuid,
        models.User.is_current == True
    ).first()

    if not old_record:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. EXPIRE the old record
    now = datetime.now(timezone.utc)
    old_record.is_current = False
    old_record.end_date = now
    old_record.updated_date = now

    # 3. CREATE the new record (The new "Truth")
    new_version = models.User(
        user_uuid=user_uuid,
        first_name=first_name,
        last_name=last_name,
        email=email,
        rank=rank,
        nicknames=nicknames,
        # COPY these from the old record so they aren't lost or set to NULL
        password_hash=old_record.password_hash,
        profile_image_url=old_record.profile_image_url,
        last_graded_date=old_record.last_graded_date, 
        comments=old_record.comments,
        # SCD Metadata
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=old_record.created_date, # Keep the original birth date of the record
        updated_date=datetime.now(timezone.utc)
)

    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version

@app.post("/classes/", response_model=schemas.ClassResponse)
def create_class(
    class_name: str = Form(...),
    day: str = Form(...),
    time: str = Form(...),
    weighting: float = Form(1.0),
    description: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    new_class = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name=class_name,
        day=day,
        time=time,
        weighting=weighting,
        description=description,
        is_current=True
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class

# GET route filtered for current classes
@app.get("/classes/", response_model=list[schemas.ClassResponse])
def get_current_classes(db: Session = Depends(database.get_db)):
    return db.query(models.ClassSchedule).filter(models.ClassSchedule.is_current == True).all()


# Endpoint to fetch all users (for the Analytics UI)
@app.get("/users/", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(database.get_db)):
    return db.query(models.User).all()

# --- GYM LOCATIONS ---
@app.post("/gyms/", response_model=schemas.GymResponse)
def create_gym(gym: schemas.GymCreate, db: Session = Depends(database.get_db)):
    db_gym = models.GymLocation(**gym.model_dump())
    db.add(db_gym)
    db.commit()
    db.refresh(db_gym)
    return db_gym

@app.get("/gyms/", response_model=list[schemas.GymResponse])
def get_gyms(db: Session = Depends(database.get_db)):
    return db.query(models.GymLocation).all()

@app.put("/gyms/{gym_id}", response_model=schemas.GymResponse)
def update_gym(gym_id: int, gym_data: schemas.GymCreate, db: Session = Depends(database.get_db)):
    db_gym = db.query(models.GymLocation).filter(models.GymLocation.id == gym_id).first()
    if not db_gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    for key, value in gym_data.model_dump().items():
        setattr(db_gym, key, value)
    db.commit()
    db.refresh(db_gym)
    return db_gym

# --- CLASS TYPES ---
@app.post("/class-types/", response_model=schemas.ClassTypeResponse)
def create_class_type(ctype: schemas.ClassTypeCreate, db: Session = Depends(database.get_db)):
    db_type = models.ClassType(**ctype.model_dump())
    db.add(db_type)
    db.commit()
    db.refresh(db_type)
    return db_type

@app.get("/class-types/", response_model=list[schemas.ClassTypeResponse])
def get_class_types(db: Session = Depends(database.get_db)):
    return db.query(models.ClassType).all()

@app.get("/term-targets/", response_model=list[schemas.TermTargetResponse])
def get_all_term_targets(db: Session = Depends(database.get_db)):
    return db.query(models.TermTarget).all()

# 2. GET targets for a specific term (the primary method for the analytics view)
@app.get("/term-targets/term/{term_id}", response_model=list[schemas.TermTargetResponse])
def get_targets_by_term(term_id: int, db: Session = Depends(database.get_db)):
    targets = db.query(models.TermTarget).filter(models.TermTarget.term_id == term_id).all()
    if not targets:
        return [] # Return empty list if instructor hasn't set targets for this term yet
    return targets

# 3. PUT to update a specific target by ID
@app.put("/term-targets/{target_id}", response_model=schemas.TermTargetResponse)
def update_term_target(target_id: int, target_data: schemas.TermTargetUpdate, db: Session = Depends(database.get_db)):
    db_target = db.query(models.TermTarget).filter(models.TermTarget.id == target_id).first()
    
    if not db_target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    db_target.target = target_data.target
    db.commit()
    db.refresh(db_target)
    return db_target

@app.get("/attendance/", response_model=List[schemas.AttendanceResponse])
def get_attendance(db: Session = Depends(database.get_db)):
    records = db.query(models.FactAttendance).all()
    
    # We can manually inject the names for the frontend's convenience
    for r in records:
        # Fetch the user version associated with this UUID that is currently active
        # (Or join via relationship)
        r.user_name = f"{r.user.first_name} {r.user.last_name}"
        r.class_name = r.class_info.class_name
        
    return records

@app.get("/attendance/user/{user_uuid}", response_model=List[schemas.UserAnalyticsResponse])
def get_attendance_by_user(user_uuid: str, db: Session = Depends(database.get_db)):
    records = db.query(models.FactAttendance).options(
        joinedload(models.FactAttendance.user),
        joinedload(models.FactAttendance.class_info)
    ).filter(models.FactAttendance.user_uuid == user_uuid).all()
   
    results = []
    for r in records:
        results.append({
            "userfullname": f"{r.user.first_name} {r.user.last_name}",
            "id": r.id,
            "attendance_date": r.attendance_date,
            "user_uuid": r.user_uuid,
            "class_name": r.class_info.class_name,
            "weighting": r.class_info.weighting,
            "rank_at_time": r.user.rank
        })
    
    return results

@app.get("/attendance/class/{class_name}", response_model=list[schemas.ClassAttendanceResponse])
def get_class_attendance_detail(
    class_name: str, 
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None,
    rank_filter: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    # Start the query with joins
    query = db.query(models.FactAttendance).join(models.ClassSchedule).join(models.User)
    
    # Apply Filters dynamically
    query = query.filter(models.ClassSchedule.class_name == class_name)
    
    if start_date:
        query = query.filter(models.FactAttendance.attendance_date >= start_date)
    if end_date:
        query = query.filter(models.FactAttendance.attendance_date <= end_date)
    if rank_filter:
        query = query.filter(models.User.rank == rank_filter)
        
    records = query.options(
        joinedload(models.FactAttendance.user),
        joinedload(models.FactAttendance.class_info)
    ).all()

    return [
        {
            "id": r.id,
            "attendance_date": r.attendance_date,
            "user_uuid": r.user_uuid,
            "userfullname": f"{r.user.first_name} {r.user.last_name}",
            "rank_at_time": r.user.rank,
            "weighting": r.class_info.weighting
        } for r in records
    ]

@app.post("/attendance/", response_model=schemas.AttendanceResponse)
def record_attendance(user_uuid: str = Form(...), class_id: int = Form(...), attendance_date: str = Form(...), db: Session = Depends(database.get_db)):
    date_obj = datetime.strptime(attendance_date, "%Y-%m-%d").date()
    
    try:
        new_record = models.FactAttendance(
            user_uuid=user_uuid,
            class_id=class_id,
            attendance_date=date_obj
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="User is already checked into this class for today."
        )
    
@app.put("/classes/{class_uuid}", response_model=schemas.ClassResponse)
def update_class_schedule(
    class_uuid: str,
    class_name: str = Form(...),
    day: str = Form(...),
    time: str = Form(...),
    weighting: float = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    now = datetime.now(timezone.utc)

    # 1. Find the current active version
    old_version = db.query(models.ClassSchedule).filter(
        models.ClassSchedule.class_uuid == class_uuid,
        models.ClassSchedule.is_current == True
    ).first()

    if not old_version:
        raise HTTPException(status_code=404, detail="Class not found")

    # 2. Expire the old version
    old_version.is_current = False
    old_version.end_date = now

    # 3. Create the new version
    new_version = models.ClassSchedule(
        class_uuid=class_uuid, # Keep the same anchor
        class_name=class_name,
        day=day,
        time=time,
        weighting=weighting,
        description=description,
        is_current=True,
        effective_date=now,
        created_date=old_version.created_date # Keep original creation date
    )
    
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version

# --- TERM METHODS ---

@app.post("/terms/", response_model=schemas.TermResponse)
def create_term(term: schemas.TermCreate, db: Session = Depends(database.get_db)):
    # Optional: Check for overlapping terms
    overlap = db.query(models.Term).filter(
        models.Term.start_date <= term.end_date,
        models.Term.end_date >= term.start_date
    ).first()
    
    if overlap:
        raise HTTPException(
            status_code=400, 
            detail=f"Term dates overlap with existing term: {overlap.term_name}"
        )

    db_term = models.Term(**term.model_dump())
    db.add(db_term)
    db.commit()
    db.refresh(db_term)
    return db_term

@app.put("/terms/{term_id}", response_model=schemas.TermResponse)
def update_term(term_id: int, term_data: schemas.TermUpdate, db: Session = Depends(database.get_db)):
    db_term = db.query(models.Term).filter(models.Term.id == term_id).first()
    if not db_term:
        raise HTTPException(status_code=404, detail="Term not found")

    # Update only the fields provided
    update_dict = term_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_term, key, value)

    db.commit()
    db.refresh(db_term)
    return db_term

@app.get("/terms/", response_model=list[schemas.TermResponse])
def get_terms(db: Session = Depends(database.get_db)):
    return db.query(models.Term).order_by(models.Term.start_date.desc()).all()

app.mount("/static", StaticFiles(directory="static"), name="static")
