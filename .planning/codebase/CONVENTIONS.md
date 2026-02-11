# Coding Conventions

**Analysis Date:** 2026-02-11

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `models.py`, `database.py`, `cloudinary_service.py`)
- Router modules: `snake_case.py` in `app/routers/` (e.g., `users.py`, `class_instances.py`, `term_targets.py`)
- Test files: `test_*.py` (e.g., `test_smoke.py`, `test_role_system.py`, `test_curricula.py`)
- Streamlit pages: `PascalCase.py` for main, `N_PascalCase.py` for numbered pages (e.g., `Attendance.py`, `2_Analytics.py`, `3_Settings.py`)
- Utility scripts: `snake_case.py` (e.g., `reset_db.py`, `seed_complete_data.py`)

**Functions:**
- All functions: `snake_case` (e.g., `get_users()`, `record_attendance()`, `create_teacher_token()`)
- API endpoints: `snake_case` (e.g., `def create_user(...)`, `def get_attendance_by_user(...)`)
- Private/helper functions: `_snake_case` with leading underscore (e.g., `_process_image()`, `_user_class_date_uc`)

**Variables:**
- Local variables: `snake_case` (e.g., `user_uuid`, `attendance_date`, `parsed_date`)
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `BASE_URL`, `SQLALCHEMY_DATABASE_URL`, `ALGORITHM`)
- Environment variables: `UPPER_SNAKE_CASE` (e.g., `SECRET_KEY`, `DATABASE_URL`, `CLOUDINARY_CLOUD_NAME`)

**Classes:**
- All classes: `PascalCase` (e.g., `User`, `FactAttendance`, `ClassInstance`, `UserResponse`)
- Pydantic schemas: `PascalCase` with descriptive suffixes (e.g., `UserCreate`, `UserResponse`, `TermBase`)
- SQLAlchemy models: `PascalCase` (e.g., `ClassSchedule`, `UserRole`, `ClassFeedback`)

**Database Tables:**
- Table names: `snake_case` via `__tablename__` (e.g., `"users"`, `"attendance"`, `"class_instances"`, `"term_targets"`)
- Composite names use underscores (e.g., `"class_feedback"`, `"gym_locations"`, `"user_roles"`)

**Database Columns:**
- All columns: `snake_case` (e.g., `user_uuid`, `class_id`, `attendance_date`, `is_current`)
- Boolean columns: prefix with `is_` (e.g., `is_current`, `is_active`)
- Timestamp columns: suffix with `_date` or `_at` (e.g., `created_date`, `created_at`, `effective_date`)
- Foreign keys: suffix with `_id` or `_uuid` (e.g., `class_id`, `user_uuid`, `teacher_uuid`)

## Code Style

**Formatting:**
- Tool used: None detected (manual formatting)
- Line length: Approximately 88-100 characters (not strictly enforced)
- Indentation: 4 spaces (Python standard)
- String quotes: Double quotes preferred for strings, single quotes acceptable

**Linting:**
- Tool: Ruff (cache directory present: `.ruff_cache`)
- No explicit configuration files detected (`.ruff.toml`, `ruff.toml`)
- Project relies on default Ruff rules

**Type Hints:**
- Always use type hints for function parameters and return values
- Import from `typing` module: `Optional`, `List`, `Tuple` (Python 3.9+ compatible)
- Example from `app/auth.py`:
  ```python
  def verify_password(plain_password: str, hashed_password: str) -> bool:
      return pwd_context.verify(plain_password, hashed_password)
  
  def create_teacher_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
      # implementation
  ```
- Pydantic models provide automatic type validation
- Optional fields marked with `Optional[T]` and default values (e.g., `Optional[str] = None`)

## Import Organization

**Order:**
1. Standard library imports (alphabetical)
2. Third-party imports (alphabetical)
3. Local imports (from `app` or relative imports)

**Grouping:**
- Blank line between each group
- Multiple imports from same module on single line if short
- Multi-line imports use parentheses (not backslash continuation)

**Example from `app/routers/users.py`:**
```python
import shutil
from pathlib import Path
from typing import Optional, List
from dateutil import parser
from dateutil.parser import ParserError
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..config import settings
from ..auth import get_password_hash
from ..services.cloudinary_service import cloudinary_service
```

**Example from `app/models.py`:**
```python
from .database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Date,
    Float,
    Text,
    Boolean,
    UniqueConstraint,
    and_,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, foreign
from datetime import datetime, timezone
```

**Import Conventions:**
- Use relative imports within `app` package (e.g., `from .. import models`, `from .database import Base`)
- Import specific items rather than entire modules when practical
- Use parentheses for multi-line imports from single module

## Error Handling

**Patterns:**

**API Errors - HTTPException:**
- Always use `HTTPException` from FastAPI for API errors
- Include descriptive `detail` messages
- Example from `app/routers/users.py`:
  ```python
  from fastapi import HTTPException
  
  if db_user:
      raise HTTPException(status_code=400, detail="Email already registered")
  
  if not old_record:
      raise HTTPException(status_code=404, detail="User not found")
  ```

**Database Errors - IntegrityError:**
- Catch `IntegrityError` from SQLAlchemy for constraint violations
- Always rollback database session on error
- Example from `app/routers/attendance.py`:
  ```python
  from sqlalchemy.exc import IntegrityError
  
  try:
      db.add(new_record)
      db.commit()
      db.refresh(new_record)
      return new_record
  except IntegrityError:
      db.rollback()
      raise HTTPException(
          status_code=400, detail="User is already checked into this class for today."
      )
  ```

**JWT Errors:**
- Catch `JWTError` from `jose` library for token validation
- Example from `app/auth.py`:
  ```python
  from jose import JWTError, jwt
  
  try:
      payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
      return payload
  except JWTError:
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Could not validate credentials.",
          headers={"WWW-Authenticate": "Bearer"},
      )
  ```

**Validation Errors:**
- Use Pydantic validators for input validation
- Raise `ValueError` in validators (automatically converted to 422 Unprocessable Entity)
- Example from `app/schemas.py`:
  ```python
  @field_validator("end_date")
  @classmethod
  def end_date_after_start_date(cls, v, info):
      if "start_date" in info.data and v <= info.data["start_date"]:
          raise ValueError("end_date must be after start_date")
      return v
  ```

**Generic Exception Handling:**
- Catch broad exceptions for external service failures (e.g., Cloudinary uploads)
- Provide user-friendly error messages
- Example from `app/routers/users.py`:
  ```python
  try:
      upload_result = cloudinary_service.upload_profile_photo(...)
  except ValueError as e:
      raise HTTPException(status_code=400, detail=f"Image validation failed: {str(e)}")
  except Exception as e:
      raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
  ```

## Logging

**Framework:** None (uses console output)

**Patterns:**
- Commented-out debug statements preserved in code for developer reference
- Example from `app/routers/users.py`:
  ```python
  # Debug: Uncomment to check file upload details
  # print(
  #     f"DEBUG: Received file: {file.filename}, size: {len(original_image_bytes)} bytes, type: {file.content_type}"
  # )
  ```
- No structured logging framework (e.g., `logging` module) in use
- Future: Consider implementing proper logging via `logging` module

## Comments

**When to Comment:**
- Module-level docstrings for all routers and modules
- Function docstrings for complex or public API functions
- Inline comments for non-obvious business logic
- SCD Type 2 versioning steps (numbered comments in update operations)

**Docstring Format:**
- Triple-quoted strings (`"""..."""`)
- Brief summary line for simple functions
- Multi-line docstrings for complex operations with Args/Returns sections
- Example from `app/services/cloudinary_service.py`:
  ```python
  def _process_image(
      self,
      image_bytes: bytes,
      target_size: Tuple[int, int] = (400, 400),
      quality: int = 80,
  ) -> bytes:
      """
      Process image: resize, compress, strip EXIF data.
  
      Args:
          image_bytes: Raw image bytes
          target_size: Target dimensions (width, height)
          quality: JPEG quality (1-100)
  
      Returns:
          Processed image bytes
      """
  ```

**Inline Comment Style:**
- Use `#` for single-line comments
- Capitalize first word, use proper punctuation for full sentences
- Comment SCD Type 2 versioning steps with numbered comments:
  ```python
  # 1. Find the CURRENT active record for this person
  old_record = db.query(models.User).filter(...).first()
  
  # 2. Handle image upload if provided
  image_url = old_record.profile_image_url
  
  # 3. EXPIRE the old record
  old_record.is_current = False
  
  # 4. CREATE the new record
  new_version = models.User(...)
  ```

**JSDoc/TSDoc:**
- Not applicable (Python project)

## Function Design

**Size:**
- API endpoint functions: 50-150 lines (includes error handling and business logic)
- Helper functions: 10-50 lines
- Complex operations broken into numbered steps with comments

**Parameters:**
- FastAPI endpoints use dependency injection: `db: Session = Depends(get_db)`
- Form data endpoints use `Form(...)` for each parameter
- File uploads use `File(...)` with `Optional[UploadFile]`
- Required parameters: `= Form(...)` or `= File(...)`
- Optional parameters: `= Form(None)` or `= File(None)`
- Example:
  ```python
  def create_user(
      first_name: str = Form(...),
      last_name: str = Form(...),
      email: str = Form(...),
      password: str = Form(...),
      rank: Optional[str] = Form(None),
      file: Optional[UploadFile] = File(None),
      db: Session = Depends(get_db),
  ):
  ```

**Return Values:**
- API endpoints return Pydantic models or dictionaries
- Always specify `response_model` in route decorator
- Example:
  ```python
  @router.post("/", response_model=schemas.UserResponse)
  def create_user(...):
      return new_user
  
  @router.get("/", response_model=List[schemas.UserResponse])
  def get_users(...):
      return db.query(models.User).all()
  ```

**Datetime Handling:**
- Always use timezone-aware datetimes: `datetime.now(timezone.utc)`
- Use `Date` type for date-only fields (e.g., `attendance_date`, `start_date`, `end_date`)
- Use `DateTime` type for timestamps (e.g., `created_at`, `updated_at`, `effective_date`)
- Parse string dates with `dateutil.parser.parse()`:
  ```python
  from dateutil import parser
  
  parsed_date = parser.parse(last_graded_date).date()
  ```

**SCD Type 2 Update Pattern:**
- Follow this pattern for all SCD Type 2 updates (User, ClassSchedule, UserRole):
  ```python
  # 1. Find current record
  old_record = db.query(Model).filter(
      Model.uuid == uuid,
      Model.is_current == True
  ).first()
  
  # 2. EXPIRE old record
  now = datetime.now(timezone.utc)
  old_record.is_current = False
  old_record.end_date = now
  old_record.updated_date = now
  
  # 3. CREATE new version
  new_version = Model(
      uuid=uuid,  # Keep same anchor
      is_current=True,
      effective_date=datetime.now(timezone.utc),
      created_date=old_record.created_date,  # Preserve original
      # ... updated fields
  )
  db.add(new_version)
  db.commit()
  db.refresh(new_version)
  ```

## Module Design

**Exports:**
- APIRouter instances exported from router modules
- Routers registered in `app/main.py` via `app.include_router()`
- Example router setup in `app/routers/users.py`:
  ```python
  router = APIRouter(prefix="/users", tags=["users"])
  ```

**Router Organization:**
- One router per resource type (`users.py`, `classes.py`, `attendance.py`)
- Related endpoints grouped in same router
- Complex resources have dedicated routers (e.g., `class_instances.py`, `term_targets.py`)

**Barrel Files:**
- Not used (explicit imports preferred)
- `app/__init__.py` is empty

**Pydantic Schemas (v2):**
- Use `BaseModel` from Pydantic v2
- Use `field_validator` decorator (NOT `@validator` from v1)
- Set `Config.from_attributes = True` for ORM compatibility
- Use `EmailStr` for email validation (requires `pydantic[email]`)
- Example:
  ```python
  from pydantic import BaseModel, EmailStr, field_validator
  
  class UserResponse(BaseModel):
      id: int
      email: str
      
      class Config:
          from_attributes = True
  
      @field_validator('email')
      @classmethod
      def email_must_be_lowercase(cls, v):
          return v.lower()
  ```

**Configuration Management:**
- Settings class in `app/config.py` loads from environment variables
- Global `settings` instance exported: `from .config import settings`
- Environment variables loaded via `python-dotenv` in `app/database.py` and `app/auth.py`
- Default values provided for all settings

---

*Convention analysis: 2026-02-11*
