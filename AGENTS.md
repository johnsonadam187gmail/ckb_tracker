# AGENTS.MD - CKB Tracker Development Guide

## Project Overview
**CKB Tracker** is an attendance tracking application for martial arts classes. Built with FastAPI backend, SQLAlchemy ORM, SQLite database, and Streamlit frontend.

**Tech Stack:**
- Backend: FastAPI 0.127.0+ with Uvicorn
- Database: SQLAlchemy 2.0+ with SQLite
- Frontend: Streamlit 1.52.2+
- Validation: Pydantic v2 (with email support)
- Auth: Passlib with bcrypt

## Operational Guidelines
Before moving from one task to the next, you must verify changes by running the relevant test suite (npm test) or by using the terminal to check the output/logs. Do not assume code works just because it compiles. Develop tests as you work on developing features, to ensure a full suite of tests, and that testing can be conducted and is successful after every feature add or change. 

## Definition of Done
"A task is only 'Done' once it has been: 1. Written, 2. Linted, 3. Verified via terminal output, 4. tested by relevant test cases."

## Build, Run & Test Commands

### Environment Setup
```bash
# Create virtual environment (Python 3.12+)
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix/Mac

# Install dependencies
pip install -e .
```

### Running the Application
```bash
# Start FastAPI backend (port 8000)
uvicorn app.main:app --reload

# Start Streamlit frontend (port 8501)
streamlit run Attendance.py
```

### Database Operations
```bash
# Reset database (drops all tables and recreates)
python reset_db.py
```

### Testing
**Note:** No test suite currently exists. When creating tests:
```bash
# Install pytest first
pip install pytest pytest-cov

# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run specific test function
pytest tests/test_models.py::test_user_creation

# Run with coverage
pytest --cov=app tests/
```

## Project Structure
```
ckb_tracker/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + all routes
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   └── database.py      # DB connection & session
├── pages/               # Streamlit additional pages
│   ├── 2_Analytics.py
│   └── 3_Settings.py
├── static/
│   └── profile_pics/    # User profile images
├── backups/             # Backup files
├── Attendance.py        # Main Streamlit app
├── reset_db.py          # Database reset utility
├── pyproject.toml       # Dependencies
├── test.db              # SQLite database
└── CONTEXT.md           # Project context/instructions
```

## Code Style Guidelines

### Import Order
Follow this order with blank lines between groups:
1. Standard library imports
2. Third-party imports (FastAPI, SQLAlchemy, Pydantic, etc.)
3. Local imports (from app import ...)

**Example:**
```python
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone, date

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, EmailStr

from app import models, database, schemas
from .database import get_db
```

### Type Hints
- **Always** use type hints for function parameters and return values
- Use `Optional[T]` for nullable fields
- Use `List[T]` from typing for list types (or `list[T]` for Python 3.9+)
- Pydantic models automatically validate types

**Example:**
```python
def create_user(
    first_name: str,
    last_name: str,
    email: str,
    rank: Optional[str] = None,
    db: Session = Depends(get_db)
) -> schemas.UserResponse:
    pass
```

### Naming Conventions
- **Variables/Functions:** `snake_case` (e.g., `user_uuid`, `get_users()`)
- **Classes:** `PascalCase` (e.g., `User`, `FactAttendance`, `UserResponse`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `BASE_URL`, `UPLOAD_DIR`)
- **Database Tables:** `snake_case` via `__tablename__` (e.g., "users", "term_targets")
- **Private/Internal:** Prefix with `_` (e.g., `_helper_function`)

### Database Patterns

#### Slowly Changing Dimensions (SCD Type 2)
This app uses SCD Type 2 for Users and Classes:
```python
# Required fields for SCD Type 2
is_current = Column(Boolean, default=True)
effective_date = Column(DateTime, default=datetime.now(timezone.utc))
end_date = Column(DateTime, nullable=True)
created_date = Column(DateTime)  # Original creation
updated_date = Column(DateTime, onupdate=datetime.now(timezone.utc))
```

#### UUID Anchors
- Use `user_uuid` and `class_uuid` as stable identifiers
- `id` is auto-incrementing primary key for each version
- Foreign keys reference UUIDs, not IDs

#### Update Pattern (SCD Type 2)
```python
# 1. Find current record
old_record = db.query(Model).filter(
    Model.uuid == uuid,
    Model.is_current == True
).first()

# 2. Expire old record
old_record.is_current = False
old_record.end_date = datetime.now(timezone.utc)

# 3. Create new version
new_version = Model(
    uuid=uuid,  # Keep same anchor
    is_current=True,
    effective_date=datetime.now(timezone.utc),
    created_date=old_record.created_date,  # Preserve original
    # ... updated fields
)
db.add(new_version)
db.commit()
```

### Pydantic Schemas (v2)
- Use `BaseModel` from `pydantic`
- Use `field_validator` decorator (NOT `@validator` from v1)
- Set `Config.from_attributes = True` for ORM models
- Use `EmailStr` for email validation (requires `pydantic[email]`)

**Example:**
```python
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    first_name: str
    email: EmailStr
    
    class Config:
        from_attributes = True

    @field_validator('email')
    @classmethod
    def email_must_be_lowercase(cls, v):
        return v.lower()
```

### Error Handling
- Use `HTTPException` for API errors
- Use `IntegrityError` from SQLAlchemy for constraint violations
- Always rollback on database errors
- Provide meaningful error messages

**Example:**
```python
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

try:
    db.add(new_record)
    db.commit()
except IntegrityError:
    db.rollback()
    raise HTTPException(
        status_code=400,
        detail="User is already checked into this class for today."
    )
```

### DateTime Handling
- **Always** use timezone-aware datetimes: `datetime.now(timezone.utc)`
- Use `Date` type for date-only fields (attendance_date, term dates)
- Use `DateTime` for timestamps
- Parse string dates with `dateutil.parser.parse()`

### FastAPI Endpoints

#### Response Models
Always specify `response_model`:
```python
@app.get("/users/", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()
```

#### Form Data with Files
Use `Form(...)` and `File(...)`:
```python
@app.post("/users/")
def create_user(
    first_name: str = Form(...),
    email: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    pass
```

#### Query Filters
Always filter by `is_current=True` for SCD Type 2 tables:
```python
db.query(models.User).filter(models.User.is_current == True).all()
```

## Database Models

### Core Entities
1. **User** - Members with SCD Type 2 versioning
2. **ClassSchedule** - Classes with SCD Type 2 versioning
3. **FactAttendance** - Attendance fact table with unique constraint
4. **Term** - Training terms/semesters
5. **TermTarget** - Performance targets per rank per term
6. **GymLocation** - Training locations
7. **ClassType** - Class categories (Gi, No-Gi, etc.)

### Key Constraints
- `FactAttendance`: Unique constraint on (user_uuid, class_id, attendance_date)
- `User.email`: Indexed but not unique (due to versioning)
- `User.user_uuid`: Unique identifier for user identity
- `ClassSchedule.class_uuid`: Unique identifier for class identity

## Common Pitfalls

1. **Forgetting is_current filter** - Always filter SCD Type 2 tables by `is_current=True`
2. **Using id instead of uuid** - Foreign keys should reference uuid fields, not id
3. **Naive datetimes** - Always use `datetime.now(timezone.utc)`
4. **Pydantic v1 patterns** - This project uses Pydantic v2 (`field_validator` not `@validator`)
5. **Not preserving old data** - When creating new SCD versions, copy fields that shouldn't change

## API Conventions

- Base URL: `http://127.0.0.1:8000`
- Use plural nouns: `/users/`, `/classes/`, `/terms/`
- UUID in path: `/users/{user_uuid}`, `/classes/{class_uuid}`
- Filter endpoints: `/attendance/user/{user_uuid}`, `/term-targets/term/{term_id}`
- Return empty lists (not 404) when no results found
- Upsert pattern: POST creates, PUT updates (with SCD versioning)

## Development Workflow

1. **Models First** - Define SQLAlchemy models in `app/models.py`
2. **Schemas Next** - Create Pydantic schemas in `app/schemas.py`
3. **Routes Last** - Add endpoints to `app/main.py`
4. **Frontend Integration** - Update Streamlit pages to consume API
5. **Test Manually** - No automated tests yet; test via UI or curl/Postman
