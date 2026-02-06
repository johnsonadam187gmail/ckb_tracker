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
The project now has a comprehensive test suite. Run tests with:
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
├── assets/              # UI styling assets
│   ├── style.css        # Main component styles
│   ├── dark-theme.css   # Dark mode color palette
│   └── light-theme.css  # Light mode color palette
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
2. **Role** - Fixed role types (Student, Teacher, Admin)
3. **UserRole** - Many-to-many user-role assignments with SCD Type 2 versioning
4. **ClassSchedule** - Classes with SCD Type 2 versioning
5. **ClassInstance** - Specific class occurrence (class + date) with teacher and lesson info
6. **FactAttendance** - Attendance fact table linked to ClassInstances
7. **Term** - Training terms/semesters
8. **TermTarget** - Performance targets per rank per term
9. **GymLocation** - Training locations
10. **ClassType** - Class categories (Gi, No-Gi, etc.)

### Role System Architecture

**Overview:** The application implements a role-based system for tracking user permissions and responsibilities with complete historical tracking.

**Three Fixed Roles:**
- **Student** (Default) - Assigned automatically on user creation
- **Teacher** - Instructors who teach classes
- **Admin** - Administrators with full access (future RBAC implementation)

**Key Design Principles:**
- Many-to-many relationship: Users can have multiple roles simultaneously
- Historical tracking: All role assignments/removals are tracked with SCD Type 2
- Teacher tracking: Attendance records capture which teacher taught each class
- Default behavior: New users automatically receive Student role

**Database Schema:**

```python
# Role Table (Static reference)
class Role(Base):
    id = Integer (PK)
    name = String (Unique: Student, Teacher, Admin)
    description = Text

# UserRole Table (SCD Type 2 junction table)
class UserRole(Base):
    id = Integer (PK)
    user_uuid = String (FK → users.user_uuid)
    role_id = Integer (FK → roles.id)
    is_current = Boolean (Indexed)
    effective_date = DateTime
    end_date = DateTime (Nullable)
    created_date = DateTime
    updated_date = DateTime

# FactAttendance (Enhanced with role tracking)
class FactAttendance(Base):
    id = Integer (PK)
    user_uuid = String (FK → users.user_uuid) # Student attending
    class_id = Integer (FK → classes.id)
    teacher_uuid = String (FK → users.user_uuid) # Teacher who taught
    user_role_id = Integer (FK → user_roles.id) # Role at time of attendance
    attendance_date = Date
    created_at = DateTime
    UNIQUE(user_uuid, class_id, attendance_date)
```

**Role Assignment Flow:**

1. **User Creation:**
   ```python
   # Automatically assigns Student role
   POST /users/ → Creates user → Assigns Student role
   ```

2. **Role Management (Settings Page Only):**
   ```python
   # Get current roles
   GET /roles/user/{user_uuid}
   
   # Update roles (SCD Type 2 pattern)
   PUT /roles/user/{user_uuid}
   Body: {"role_ids": [1, 2]}  # Assign Student + Teacher
   
   # View role history
   GET /roles/user/{user_uuid}/history
   ```

3. **Attendance Check-In:**
   ```python
   # Always records as Student, includes optional teacher
   POST /attendance/
   Body: {
       "user_uuid": "student-uuid",
       "class_id": 1,
       "attendance_date": "2026-01-31",
       "teacher_uuid": "teacher-uuid"  # Optional
   }
   ```

**Role Update Pattern (SCD Type 2):**

```python
# Example: Change user from Student to Teacher
# 1. Get current roles
current_roles = db.query(UserRole).filter(
    UserRole.user_uuid == uuid,
    UserRole.is_current == True
).all()

# 2. Expire removed roles
for role in current_roles:
    if role.role_id not in new_role_ids:
        role.is_current = False
        role.end_date = datetime.now(timezone.utc)

# 3. Add new roles
for role_id in new_role_ids:
    if role_id not in current_role_ids:
        new_assignment = UserRole(
            user_uuid=uuid,
            role_id=role_id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        db.add(new_assignment)
```

**Analytics & Reporting:**

- **Student Analytics:** Tracks attendance, points, targets (existing functionality)
- **Teacher Analytics:** New view showing:
  - Classes taught
  - Student counts per class
  - Teaching history over time
  - Accessible via: `GET /attendance/teacher/{teacher_uuid}/classes`

**Frontend Integration:**

1. **Attendance Page (`Attendance.py`):**
   - Teacher selection dropdown (fetches users with Teacher role)
   - Optional field - not required for check-in
   
2. **Settings Page (`pages/3_Settings.py`):**
   - Role management section per user
   - Multi-select checkboxes for role assignment
   - Role history viewer (collapsible)
   
3. **Analytics Page (`pages/2_Analytics.py`):**
   - Automatic role detection
   - Switches between Student/Teacher analytics views
   - Radio button selector if user has both roles

**API Endpoints:**

```
GET    /roles/                          # List all roles
GET    /roles/user/{user_uuid}          # Get user's current roles
GET    /roles/user/{user_uuid}/history  # Get role history
PUT    /roles/user/{user_uuid}          # Update user roles
GET    /roles/users/by-role/{role_name} # Get all users with role
GET    /attendance/teacher/{uuid}/classes # Teacher analytics
```

### ClassInstance (Lessons) Architecture

**Overview:** The application implements a lesson management system to track lesson plans, video resources, and teacher assignments for each specific class occurrence.

**Key Concept:**
- **ClassSchedule**: Represents a recurring class (e.g., "Fundamentals 1 - Monday 18:00")
- **ClassInstance**: Represents a specific occurrence of a class on a particular date (e.g., "Fundamentals 1 on 2026-01-31")
- **Lesson Data**: Attached to ClassInstance (title, lesson plan URL, video folder URL)
- **Teacher Assignment**: Now at ClassInstance level (one teacher per class occurrence)

**Why ClassInstance?**
- Separates "scheduled class" from "class happening on a date"
- Allows different lesson plans for the same recurring class
- Enables teacher assignment at class level (not per-student)
- Supports curriculum progression tracking
- Auto-created when first student checks in (if not pre-created by admin)

**Database Schema:**

```python
class ClassInstance(Base):
    __tablename__ = "class_instances"
    
    id = Integer (PK)
    class_id = Integer (FK → classes.id, NOT NULL, Indexed)
    class_date = Date (NOT NULL, Indexed)
    teacher_uuid = String (FK → users.user_uuid, Nullable)
    
    # Lesson fields (all optional)
    lesson_title = String(200, Nullable)
    lesson_plan_url = String(500, Nullable)  # Validated as URL
    video_folder_url = String(500, Nullable)  # Validated as URL
    
    created_at = DateTime
    updated_at = DateTime
    
    UNIQUE(class_id, class_date)  # One instance per class per day
```

**FactAttendance Integration:**

```python
class FactAttendance(Base):
    # ... existing fields ...
    class_instance_id = Integer (FK → class_instances.id, Nullable, Indexed)
    teacher_uuid = String (Deprecated - use class_instance.teacher_uuid)
    
    # Relationship
    class_instance = relationship("ClassInstance")
```

**Data Flow:**

1. **Attendance Check-in:**
   - User checks in via Attendance page
   - Backend finds or auto-creates ClassInstance for (class_id, date)
   - Creates FactAttendance record linked to ClassInstance
   - Multiple students in same class share one ClassInstance

2. **Lesson Management (Admin):**
   - Admin goes to Settings → Lessons tab
   - Selects class + date, adds lesson info (title, URLs)
   - Creates or updates ClassInstance
   - Can pre-create for future classes or update past classes

3. **Teacher View:**
   - Teacher goes to Teacher page
   - Selects class + date
   - Sees student roster AND lesson information
   - Links to lesson plan and video folder displayed

**Lesson Management Features:**
- **Create/Update Lessons**: Settings page → Lessons tab
- **View Lessons**: Teacher page (read-only for teachers)
- **URL Validation**: Supports Google Drive, Dropbox, any valid HTTP/HTTPS URL
- **Optional Fields**: All lesson fields (title, URLs) are optional
- **Teacher Assignment**: Per class instance, affects all students in that class
- **Auto-Creation**: ClassInstance created automatically on first check-in if not exists

**API Endpoints:**

```
POST   /class-instances/              # Create/update class instance (upsert)
GET    /class-instances/              # List all instances (filters: class_id, date range)
GET    /class-instances/{id}          # Get specific instance by ID
GET    /class-instances/by-date/      # Get instance by class_id + class_date
PUT    /class-instances/{id}          # Update lesson information
DELETE /class-instances/{id}          # Delete instance (fails if attendance exists)
```

**Frontend Integration:**

1. **Settings Page (`pages/3_Settings.py`):**
   - New "📚 Lessons" tab
   - Form: Select class + date + teacher + lesson info
   - Table: View all lessons with filters (class, date range)
   - Actions: Edit, Delete lessons
   - Admin-only access (existing Settings auth)

2. **Teacher Page (`pages/4_Teacher.py`):**
   - After student roster section
   - "📚 Lesson Information" section
   - Displays: Lesson title, lesson plan button, video folder button
   - Shows "No lesson available" if not created
   - Read-only for teachers

3. **Attendance Page (`Attendance.py`):**
   - No changes needed (teacher selection removed)
   - Check-in auto-creates ClassInstance behind the scenes

### Teacher Assignment Workflow

**Overview:** Teachers are assigned at the ClassInstance level (one teacher per class occurrence), not per individual student attendance record. This feature enables both active teaching assignments and administrative corrections.

**Key Design:**
- `class_instances.teacher_uuid` (FK → users.user_uuid, Nullable) - **Primary** teacher field
- `attendance.teacher_uuid` (Deprecated) - Legacy field, replaced by class_instance relationship
- Teacher assignments can be made before students check in (pre-assignment)
- All students in a class automatically reference the teacher via ClassInstance

**Assignment Flows:**

#### 1. Teacher Dashboard (Primary Flow - Active Teaching)

**Purpose:** Teachers assign themselves (or others) to classes they are actively teaching.

**Location:** `pages/4_Teacher.py`

**User Journey:**
1. Teacher opens Teacher Dashboard
2. Selects class from dropdown
3. Selects date (defaults to today)
4. Teacher dropdown pre-populated if already assigned (fetched from ClassInstance)
5. Selects teacher from dropdown (filtered to only Teacher role users)
6. Clicks "✅ Assign {teacher name} to All Students" button
7. System makes **single API call** to ClassInstance:
   - If ClassInstance exists: `PUT /class-instances/{id}` with `{"teacher_uuid": uuid}`
   - If not exists: `POST /class-instances/` creating new instance
8. Success toast notification appears
9. Page refreshes showing updated teacher in metrics
10. All students in roster automatically linked to teacher

**Key Features:**
- Pre-fetches ClassInstance to show current teacher
- Works even with no students checked in (pre-assignment)
- Efficient single API call (not looping through students)
- Shows teacher in "Current Teacher" metric
- Toast notification for better UX
- Optimized lesson info display (reuses fetched ClassInstance)

**Code Flow:**
```python
# Fetch ClassInstance on page load
GET /class-instances/by-date/?class_id={id}&class_date={date}

# On button click - update or create
if class_instance_exists:
    PUT /class-instances/{instance_id}
    Body: {"teacher_uuid": "selected-uuid"}
else:
    POST /class-instances/
    Body: {
        "class_id": class_id,
        "class_date": "2026-02-01",
        "teacher_uuid": "selected-uuid",
        "lesson_id": null
    }
```

#### 2. Settings Page (Admin Flow - Corrections/Management)

**Purpose:** Admins manage teacher assignments after the fact, including updates and removals.

**Location:** `pages/3_Settings.py` → Lessons tab → "👨‍🏫 Teacher Assignments" subtab

**Features:**

**A. Assignment Form:**
- Class dropdown (all classes)
- Date picker (any date - past, present, future)
- Teacher dropdown (filtered to Teacher role users)
- "💾 Save Teacher Assignment" button
- Creates or updates ClassInstance via API (upsert pattern)

**B. Assignments Table:**
- Columns: Class | Date | Teacher | Lesson | (Actions)
- Filters:
  - Class dropdown (filter by specific class or all)
  - Teacher dropdown (filter by specific teacher or all)
  - Date range (from/to date pickers)
- Metrics display:
  - Total Instances
  - Teachers Assigned (count)
  - Unique Teachers (distinct count)
- Shows "Not Assigned" for null teachers
- Read-only display (editing via expander)

**C. Edit/Remove Interface:**
- Expander: "✏️ Edit Teacher Assignment"
- Select class instance from dropdown (formatted as "Class - Date")
- Shows current teacher name
- Form to update teacher (dropdown + button)
- "🗑️ Remove Teacher Assignment" button (sets teacher_uuid to None)

**User Journey:**
1. Admin opens Settings → Lessons → Teacher Assignments
2. Views table of all current assignments with filters
3. To assign/update:
   - Fills form: class, date, teacher
   - Clicks "Save" button
   - System creates or updates ClassInstance
4. To edit existing:
   - Opens "Edit" expander
   - Selects instance from dropdown
   - Updates teacher or removes assignment
5. Table refreshes showing changes

**Code Flow:**
```python
# Fetch all instances with filters
GET /class-instances/
Params: {
    class_id: (optional),
    teacher_uuid: (optional),
    start_date: "2026-01-01",
    end_date: "2026-02-01"
}

# Assign teacher (form submission)
# Check if exists
GET /class-instances/by-date/?class_id={id}&class_date={date}

if exists:
    PUT /class-instances/{id}
    Body: {"teacher_uuid": "new-uuid" or null}
else:
    POST /class-instances/
    Body: {full instance data with teacher_uuid}

# Remove teacher (button click)
PUT /class-instances/{id}
Body: {"teacher_uuid": null}
```

**Validation:**
- **Frontend:** Only users with Teacher role appear in dropdown
  - Fetched via: `GET /roles/users/by-role/Teacher`
- **Backend:** Teacher role validated when updating (attendance.py lines 291-306)
- **Optional Field:** teacher_uuid allows NULL (no teacher assigned)

**API Endpoints:**

```python
# Get teachers list
GET /roles/users/by-role/Teacher
Response: [
    {"user_uuid": "uuid", "first_name": "John", "last_name": "Doe", ...},
    ...
]

# Get ClassInstance (includes teacher info via join)
GET /class-instances/by-date/?class_id={id}&class_date={date}
Response: {
    "id": 1,
    "class_id": 1,
    "class_date": "2026-02-01",
    "teacher_uuid": "uuid",
    "teacher_name": "John Doe",  # Populated from join
    "lesson_id": null,
    "lesson_title": null,
    ...
}

# Create ClassInstance with teacher (upsert pattern)
POST /class-instances/
Body: {
    "class_id": 1,
    "class_date": "2026-02-01",
    "teacher_uuid": "uuid-here",
    "lesson_id": null
}

# Update teacher assignment
PUT /class-instances/{instance_id}
Body: {
    "teacher_uuid": "new-uuid"  # or null to remove
}

# Query with filters (Settings table)
GET /class-instances/
Params: {
    class_id: 1,  # optional
    teacher_uuid: "uuid",  # optional
    start_date: "2026-01-01",  # optional
    end_date: "2026-02-01"  # optional
}
Response: [
    {
        "id": 1,
        "class_name": "Fundamentals 1",  # Join field
        "class_date": "2026-02-01",
        "teacher_name": "John Doe",  # Join field
        "lesson_title": "Guard Passing",  # Join field
        ...
    },
    ...
]
```

**Edge Cases & Handling:**

1. **Deleted Teacher User:**
   - ClassInstance.teacher_uuid becomes dangling reference
   - UI shows "Unknown Teacher" or "Not Assigned"
   - No database cascade (preserves historical data)

2. **No Students Checked In:**
   - Teacher assignment still allowed (pre-assignment)
   - ClassInstance created without attendance records
   - When students check in later, they link to existing instance

3. **Multiple Simultaneous Updates:**
   - Last write wins at database level
   - No locking mechanism (acceptable for this use case)
   - Unlikely scenario in practice

4. **Future Date Assignment:**
   - Fully supported (pre-assignment for upcoming classes)
   - ClassInstance created in advance
   - Visible in Settings table immediately

**Database Verification:**

```sql
-- Check teacher assignment
SELECT 
    ci.id,
    ci.class_date,
    ci.teacher_uuid,
    u.first_name || ' ' || u.last_name as teacher_name
FROM class_instances ci
LEFT JOIN users u ON ci.teacher_uuid = u.user_uuid AND u.is_current = 1
WHERE ci.class_id = ?;

-- Verify attendance links to instance
SELECT 
    a.id,
    a.user_uuid,
    a.class_instance_id,
    ci.teacher_uuid as instance_teacher
FROM attendance a
JOIN class_instances ci ON a.class_instance_id = ci.id
WHERE a.class_id = ? AND a.attendance_date = ?;
```

**Testing Checklist:**

**Teacher Dashboard:**
- [ ] Dropdown pre-populates with current teacher
- [ ] Assignment works with no students (pre-assignment)
- [ ] Assignment updates existing ClassInstance
- [ ] Toast notification appears on success
- [ ] Current teacher shows in metrics
- [ ] Only Teacher role users in dropdown

**Settings Page:**
- [ ] Table displays all assignments with correct columns
- [ ] Filters work (class, teacher, date range)
- [ ] Metrics calculate correctly
- [ ] Assignment form creates/updates ClassInstance
- [ ] Edit expander allows changing teacher
- [ ] Remove button sets teacher_uuid to null
- [ ] Teacher column shows in lesson assignments table

**Backend:**
- [ ] ClassInstance.teacher_uuid persists correctly
- [ ] Attendance records reference correct instance
- [ ] API responses include teacher_name (join field)
- [ ] Teacher role validation works

**URL Validation:**
- Pydantic `HttpUrl` type validates URLs
- Accepts: `http://`, `https://` protocols
- Supports: Google Drive, Dropbox, OneDrive, any web URL
- Frontend: Shows helpful hints/examples

**Teacher Assignment Migration:**
- **Old**: `teacher_uuid` in FactAttendance (per-student)
- **New**: `teacher_uuid` in ClassInstance (per-class occurrence)
- **Benefit**: Teachers teach classes, not individual students
- **Backward Compatibility**: Old `teacher_uuid` field kept in FactAttendance but deprecated

### Curriculum Management Architecture

**Overview:** The application implements a comprehensive curriculum management system that allows admins to organize lessons into structured curricula and assign them to class instances.

**Key Concepts:**
- **Curriculum**: A collection of lessons for a specific class (1:1 relationship with ClassSchedule)
- **Lesson**: A reusable unit of instruction within a curriculum (title, description, URLs)
- **Curriculum-Lesson Assignment**: Lessons linked to class instances for tracking progression

**Why Curriculum Management?**
- Organize training into structured learning paths
- Track curriculum progression over time
- Reuse lesson content across multiple class dates
- Centralize lesson plans and video resources
- Enable systematic skill development tracking

**Database Schema:**

```python
class Curriculum(Base):
    __tablename__ = "curricula"
    
    id = Integer (PK)
    class_id = Integer (FK → classes.id, NOT NULL, Unique, Indexed)
    name = String(200, NOT NULL)
    description = Text (Nullable)
    created_at = DateTime
    updated_at = DateTime
    
    # Relationships
    class_schedule = relationship("ClassSchedule")
    lessons = relationship("Lesson", back_populates="curriculum", cascade="all, delete-orphan")

class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Integer (PK)
    curriculum_id = Integer (FK → curricula.id, NOT NULL, Indexed)
    title = String(200, NOT NULL)
    description = Text (Nullable)
    lesson_plan_url = String(500, Nullable)  # Validated as HttpUrl
    video_folder_url = String(500, Nullable)  # Validated as HttpUrl
    created_at = DateTime
    updated_at = DateTime
    
    # Relationships
    curriculum = relationship("Curriculum", back_populates="lessons")

# ClassInstance updated to reference lessons
class ClassInstance(Base):
    lesson_id = Integer (FK → lessons.id, Nullable, Indexed)
    lesson = relationship("Lesson")
```

**Data Flow:**

1. **Curriculum Creation:**
   - Admin creates curriculum for a class (Settings → Curricula tab)
   - Name auto-generated from class name if not provided
   - One curriculum per class (enforced at database level)

2. **Lesson Management:**
   - Admin adds lessons to curriculum (Settings → Lesson Library tab)
   - Lessons include title, description, lesson plan URL, video folder URL
   - URLs validated for proper format (HttpUrl)
   - Multiple lessons per curriculum

3. **Lesson Assignment:**
   - Admin assigns lesson to class instance on specific date
   - Links lesson to ClassInstance record
   - Visible to teachers via Teacher page

4. **Teacher View:**
   - Teachers see assigned lesson for their classes
   - Access lesson plan and video folder links
   - View student roster for class occurrence

**Curriculum Workflow:**

```python
# 1. Create curriculum for class
POST /curricula/
Body: {
    "class_id": 1,
    "name": "Fundamentals 1 Curriculum",  # Optional, auto-generated
    "description": "Core techniques for beginners"
}

# 2. Add lessons to curriculum
POST /lessons/
Body: {
    "curriculum_id": 1,
    "title": "Guard Passing Fundamentals",
    "description": "Learn basic guard passing techniques",
    "lesson_plan_url": "https://docs.google.com/document/d/abc123",
    "video_folder_url": "https://drive.google.com/drive/folders/xyz789"
}

# 3. Assign lesson to class instance
POST /class-instances/
Body: {
    "class_id": 1,
    "class_date": "2026-02-01",
    "lesson_id": 1,
    "teacher_uuid": "teacher-uuid"
}

# 4. Query lessons by curriculum
GET /lessons/?curriculum_id=1

# 5. Update lesson details
PUT /lessons/{lesson_id}
Body: {
    "title": "Updated Title",
    "video_folder_url": "https://drive.google.com/updated"
}
```

**Frontend Integration:**

1. **Settings Page (`pages/3_Settings.py`):**
   - **📖 Curricula Tab**:
     - Create curriculum for classes without one
     - Auto-generates name as "[Class Name] Curriculum"
     - Edit/delete curriculum (with cascade protection)
     - View all curricula in table
   
   - **📝 Lesson Library Tab**:
     - Create lessons within curriculum context
     - Add title, description, lesson plan URL, video folder URL
     - Filter lessons by curriculum
     - Edit/delete lessons
     - Validates URLs (Google Drive, Dropbox, any HTTP/HTTPS)
   
   - **📅 Assign to Dates Tab**:
     - Assign lessons to specific class instance dates
     - Select class, date, lesson, and teacher
     - View assignments in table format

2. **Teacher Page (`pages/4_Teacher.py`):**
   - After student roster section
   - "📚 Lesson Information" section
   - Displays: Lesson title, lesson plan button, video folder button
   - Shows "No lesson available" if not assigned
   - Read-only for teachers

**API Endpoints:**

```
POST   /curricula/                     # Create curriculum
GET    /curricula/                     # List all curricula (filter by class_id)
GET    /curricula/{id}                 # Get curriculum by ID
PUT    /curricula/{id}                 # Update curriculum
DELETE /curricula/{id}                 # Delete curriculum (cascades to lessons)

POST   /lessons/                       # Create lesson
GET    /lessons/                       # List all lessons (filter by curriculum_id)
GET    /lessons/{id}                   # Get lesson by ID
PUT    /lessons/{id}                   # Update lesson
DELETE /lessons/{id}                   # Delete lesson
```

**URL Validation:**
- Pydantic `HttpUrl` type validates lesson plan and video folder URLs
- Accepts: `http://`, `https://` protocols only
- Supports: Google Drive, Dropbox, OneDrive, any valid web URL
- Frontend: Shows helpful hints and examples
- Backend: Converts HttpUrl objects to strings before database storage

**Key Features:**
- **1:1 Curriculum-Class Relationship**: Each class has exactly one curriculum
- **Cascade Delete**: Deleting curriculum removes all associated lessons
- **Auto-Name Generation**: Curriculum name auto-generated from class name if not provided
- **URL Validation**: Ensures lesson plan and video URLs are valid
- **Reusable Lessons**: Lessons can be assigned to multiple class instances
- **Historical Tracking**: Created/updated timestamps for audit trail

**Test Coverage:**
- `tests/test_curricula.py`: 14 tests covering curriculum CRUD operations
- `tests/test_lessons.py`: 16 tests covering lesson CRUD operations
- `tests/test_curriculum_integration.py`: 8 integration tests for complete workflow

### Key Constraints
- `FactAttendance`: Unique constraint on (user_uuid, class_id, attendance_date)
- `ClassInstance`: Unique constraint on (class_id, class_date)
- `Curriculum.class_id`: Unique constraint (one curriculum per class)
- `User.email`: Indexed but not unique (due to versioning)
- `User.user_uuid`: Unique identifier for user identity
- `ClassSchedule.class_uuid`: Unique identifier for class identity

## Teacher Authentication & Feedback Analytics Feature

**Overview:** The application implements role-based authentication for teachers with JWT tokens and comprehensive feedback analytics for administrators. This feature ensures secure teacher access and provides privacy-conscious feedback management.

### Key Features

1. **Password-Protected User Creation**
   - All users must have passwords (minimum 6 characters)
   - Passwords hashed with Argon2 (via passlib)
   - Frontend and backend validation
   - Created users automatically assigned "Student" role

2. **Teacher Dashboard Authentication**
   - JWT-based session management
   - 5-minute token expiry with rolling window extension
   - Automatic logout on inactivity
   - Only users with "Teacher" role can access

3. **Feedback Privacy Controls**
   - **Teachers:** See anonymous feedback ("Student" only, no names)
   - **Admins:** See all feedback with full student names
   - Privacy enforced at API level

4. **Comprehensive Admin Analytics**
   - View all feedback across all classes and teachers
   - Interactive filters (date range, class, teacher, rating)
   - 4 visualization charts (Plotly)
   - CSV export functionality

### Authentication Architecture

**JWT Token Management:**

```python
# app/auth.py
- create_teacher_token(data, expires_delta) → JWT with 5-min expiry
- verify_teacher_token(token) → Validates and decodes JWT
- extend_teacher_token(token) → Rolling expiry on activity
```

**Session Flow:**

```
1. Teacher Login (pages/4_Teacher.py)
   ↓
2. POST /auth/teacher-login
   - Validates email/password
   - Checks Teacher role in UserRole table
   - Returns JWT token + user info
   ↓
3. Session Storage
   - st.session_state.teacher_token
   - st.session_state.teacher_info
   ↓
4. Activity Monitoring
   - Every page interaction: POST /auth/verify-session
   - If valid: Extend token by 5 minutes
   - If expired: Redirect to login
   ↓
5. Logout
   - Clear session state
   - Redirect to login form
```

### Database Changes

**User Model Update:**
```python
class User(Base):
    password_hash = Column(String(255), nullable=True)  # Argon2 hash
    # Note: nullable=True for backward compatibility
    # All new users require passwords
```

**No new tables added** - Uses existing User, UserRole, ClassFeedback models.

### API Endpoints

**Authentication:**
```
POST   /auth/login                  # Student login with email/password
POST   /auth/teacher-login          # Teacher login with email/password, return JWT
POST   /auth/verify-session         # Verify token, extend expiry
```

**Password Management:**
```
POST   /auth/set-password           # Set or update user password (admin)
GET    /auth/check-password/{uuid}  # Check if user has password set
DELETE /auth/remove-password/{uuid} # Remove user password (admin)
```

**Feedback:**
```
POST   /feedback/                                   # Create feedback (student)
GET    /feedback/user/{uuid}                        # Get user's feedback (student)
GET    /feedback/teacher/{uuid}                     # Teacher's feedback (anonymous)
GET    /feedback/admin/comprehensive-stats          # All feedback (admin view)
```

**Request/Response Examples:**

```python
# Student Login
POST /auth/login
Body: {
  "email": "student@ckb.com",
  "password": "student123"
}
Response: {
  "id": 1,
  "user_uuid": "...",
  "first_name": "Mike",
  "last_name": "Student",
  "email": "student@ckb.com",
  "rank": "Blue Belt",
  "profile_image_url": null,
  "is_current": true,
  ...
}

# Teacher Login
POST /auth/teacher-login
Body: username=teacher@ckb.com&password=teacher123 (form data)
Response: {
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_info": {
    "user_uuid": "...",
    "first_name": "John",
    "last_name": "Instructor",
    ...
  }
}

# Session Verification
POST /auth/verify-session
Body: {"token": "eyJ..."}
Response: {
  "status": "ok",
  "new_token": "eyJ...",
  "user_uuid": "..."
}

# Set/Update Password
POST /auth/set-password
Body: {
  "user_uuid": "user-uuid-here",
  "password": "newpassword123"
}
Response: {
  "message": "Password set successfully",
  "user_uuid": "user-uuid-here"
}

# Check Password Status
GET /auth/check-password/{user_uuid}
Response: {
  "user_uuid": "user-uuid-here",
  "has_password": true
}

# Remove Password
DELETE /auth/remove-password/{user_uuid}
Response: {
  "message": "Password removed successfully",
  "user_uuid": "user-uuid-here"
}

# Create Feedback (Student)
POST /feedback/
Body: {
  "attendance_id": 123,
  "rating": "thumbs_up",
  "comment": "Great class, learned a lot!"
}
Response: {
  "id": 1,
  "user_uuid": "user-uuid",
  "attendance_id": 123,
  "class_instance_id": 45,
  "rating": "thumbs_up",
  "comment": "Great class, learned a lot!",
  "created_at": "2026-02-06T10:30:00",
  "class_date": "2026-02-06",
  "class_name": "Fundamentals 1",
  "lesson_title": "Guard Passing"
}

# Get User's Feedback (Student)
GET /feedback/user/{user_uuid}
Response: [
  {
    "id": 1,
    "attendance_id": 123,
    "rating": "thumbs_up",
    "comment": "Great class!",
    "class_date": "2026-02-06",
    "class_name": "Fundamentals 1",
    "lesson_title": "Guard Passing"
  }
]

# Teacher Feedback (Anonymous)
GET /feedback/teacher/{teacher_uuid}
Response: [
  {
    "id": 1,
    "rating": "thumbs_up",
    "comment": "Great class!",
    "class_date": "2026-02-06",
    "class_name": "Fundamentals 1",
    "lesson_title": "Guard Passing",
    "user_full_name": null,  # Anonymous
    "teacher_name": null
  }
]

# Admin Feedback (Full Names)
GET /feedback/admin/comprehensive-stats
Response: [
  {
    "rating": "thumbs_up",
    "comment": "Great class!",
    "class_date": "2026-02-06",
    "class_name": "Fundamentals 1",
    "student_name": "Mike Student",  # Full name visible
    "teacher_name": "John Instructor"
  }
]
```

### Frontend Pages Modified

**1. Attendance.py (Main Page)**
- **Changes:** Added password fields to user creation form
- **Location:** Sidebar "Add New Member" form
- **Fields Added:**
  - Password (type="password", min 6 chars)
  - Confirm Password (validation)
- **Validation:** Frontend checks password match, minimum length
- **API Call:** Includes password in POST /users/ request

**2. pages/4_Teacher.py (Teacher Dashboard) - COMPLETE REWRITE**

**Authentication Gate:**
```python
# Shows login form if not authenticated
if "teacher_token" not in st.session_state or not verify_session():
    # Login form with email/password
    # Calls teacher_login(email, password)
    st.stop()
```

**Tab 1: Class Roster**
- Select class and date
- Assign teacher (pre-selects logged-in teacher)
- View student roster for selected class
- **Existing functionality preserved**

**Tab 2: Feedback (NEW)**
- Fetch feedback via GET /feedback/teacher/{uuid}
- Display: Date | Class | Lesson | Rating | Comment
- **Student names anonymous** - Shows no names
- Filters: Date range, Class, Rating
- Metrics: Total, Positive, Negative counts

**Sidebar:**
- Shows logged-in teacher name
- Logout button

**3. pages/3_Settings.py (Admin Settings)**
- **Changes:** Added new "📊 Feedback Analytics" tab
- **Access:** Admin-only (existing password protection)

**New Tab Structure:**
```python
st.tabs([
    "🥋 User Admin",
    "📅 Class Schedule",
    "🏢 Gyms & Types",
    "🗓️ Terms",
    "🎯 Targets",
    "📚 Lessons",
    "🔐 Student Passwords",
    "📊 Feedback Analytics"  # NEW
])
```

**Feedback Analytics Tab Components:**

1. **Metrics Row** (4 columns):
   - Total Feedback (count)
   - Positive % (thumbs_up percentage)
   - Most Active Student (by feedback count)
   - Avg Rating (percentage)

2. **Filters** (expandable):
   - Date Range (from/to date pickers)
   - Classes (multi-select)
   - Teachers (multi-select, includes "Unassigned")
   - Rating (All/Positive/Negative)

3. **Data Table**:
   - Columns: Date | Class | Student | Teacher | Rating | Comment
   - **Full student names visible** (admin view)
   - Sortable, filterable

4. **Charts** (4 visualizations):
   - Feedback Over Time (line chart, grouped by rating)
   - Feedback by Class (bar chart)
   - Feedback by Teacher (bar chart)
   - Rating Distribution (pie chart)
   - Theme-aware (uses plotly_dark/plotly_white)

5. **CSV Export**:
   - Downloads filtered data
   - Filename: `feedback_analytics_YYYYMMDD_HHMMSS.csv`

### Security Considerations

**Password Storage:**
- Hashed with Argon2 (passlib default)
- Never stored in plain text
- Backend validates password on user creation

**JWT Tokens:**
- Secret key auto-generated: `secrets.token_urlsafe(32)`
- Stored in `.env` file (gitignored)
- HS256 algorithm
- 5-minute expiry with rolling extension

**Session Management:**
- Tokens stored in Streamlit session_state (server-side)
- Not exposed to client
- Auto-cleared on logout
- Expired tokens rejected by backend

**Role Verification:**
- Teacher role checked at login
- 403 Forbidden if user lacks Teacher role
- Prevents students from accessing Teacher Dashboard

**Feedback Privacy:**
- API-level enforcement
- Teacher endpoint filters by teacher_uuid
- Admin endpoint requires Settings page authentication
- No student names returned to teacher endpoint

### Testing & Verification

**Manual Testing Guide:** See `TESTING.md` for comprehensive checklist

**Key Test Scenarios:**
1. User creation with password validation
2. Teacher login/logout flow
3. Session timeout after 5 minutes
4. Feedback privacy (teacher vs admin views)
5. Filter functionality in analytics
6. CSV export with various filters
7. Chart rendering in both themes

**Seed Data:**
Run `python seed_users.py` to create test accounts:
- Admin: admin@ckb.com / admin123
- Teacher: teacher@ckb.com / teacher123
- Student: student@ckb.com / student123

### Configuration

**Environment Variables:**
```bash
# .env file (auto-generated if not exists)
SECRET_KEY=<auto-generated-32-byte-key>
```

**Dependencies Added:**
```toml
python-jose[cryptography]  # JWT token management
```

### Migration Notes

**Existing Users Without Passwords:**
- After feature deployment, existing users have `password_hash = NULL`
- Options:
  1. Admin sets passwords via Settings → Student Passwords tab
  2. Users request password reset (if implemented)
  3. Run database migration to set default passwords

**Database Reset:**
- Feature requires fresh database with passwords
- Run `python reset_db.py` followed by `python seed_users.py`
- Existing data will be lost

### Error Handling

**Common Errors:**

1. **401 Unauthorized:**
   - Invalid or expired token
   - Incorrect email/password
   - **User Action:** Re-login

2. **403 Forbidden:**
   - User lacks Teacher role
   - **User Action:** Admin must assign Teacher role

3. **Connection Failed:**
   - Backend server not running
   - **Admin Action:** Start uvicorn server

4. **ModuleNotFoundError: 'jose':**
   - Missing dependency
   - **Admin Action:** `pip install python-jose[cryptography]`

### Performance Considerations

**JWT Token Verification:**
- Every page interaction calls /auth/verify-session
- Adds ~10-50ms overhead per request
- Acceptable for small-medium deployments

**Feedback Analytics:**
- Fetches all feedback records on tab load
- Filtering done client-side (pandas)
- May slow down with 10,000+ feedback records
- **Future Optimization:** Server-side pagination

**Chart Rendering:**
- Plotly charts load on-demand (tab activation)
- 4 charts may cause lag on slower machines
- **Future Optimization:** Lazy loading or caching

### Future Enhancements

**Potential Improvements:**
1. Password reset functionality
2. "Remember Me" option for longer sessions
3. Multi-factor authentication (MFA)
4. Role-based permissions (RBAC)
5. Feedback notifications for teachers
6. Email alerts on negative feedback
7. Feedback analytics by date range comparison

### Development Checklist

When modifying this feature:
- [ ] Update JWT secret rotation mechanism
- [ ] Add rate limiting to prevent brute force
- [ ] Implement session blacklist for logout
- [ ] Add audit logging for authentication events
- [ ] Write automated tests for auth flow
- [ ] Document API with OpenAPI schema

### Files Modified

**Backend (6 files):**
- `app/auth.py` - JWT token management functions
- `app/routers/auth.py` - Teacher login and session endpoints
- `app/routers/feedback.py` - Teacher and admin feedback endpoints
- `app/schemas.py` - Added 4 new schemas (TeacherLoginResponse, etc.)
- `app/main.py` - Included auth and feedback routers
- `app/routers/users.py` - Made password required

**Frontend (3 files):**
- `Attendance.py` - Added password fields to user form
- `pages/4_Teacher.py` - Complete rewrite with authentication
- `pages/3_Settings.py` - Added Feedback Analytics tab

**Utilities:**
- `seed_users.py` - Script to create test accounts with passwords
- `TESTING.md` - Comprehensive testing guide

### Related Documentation

- **TESTING.md:** Step-by-step manual testing guide
- **safety.md:** Implementation tracking and progress
- **API Docs:** http://127.0.0.1:8000/docs (when server running)

---

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
3. **Routes** - Create router in `app/routers/` and include in `app/main.py`
4. **Frontend Integration** - Update Streamlit pages to consume API
5. **Test** - Write tests in `tests/` and run with `pytest`
6. **Verify** - Test via UI and run full test suite

## UI Styling Guidelines

### Theme System
The application uses a hybrid light/dark theme system with dynamic CSS loading and glassmorphism design.

#### Theme Architecture
- **Main Stylesheet**: `assets/style.css` - Component styles and theme-agnostic variables
- **Dark Theme**: `assets/dark-theme.css` - Dark mode color palette (default)
- **Light Theme**: `assets/light-theme.css` - Light mode color palette
- **Streamlit Config**: `.streamlit/config.toml` - Base theme settings

#### Brand Colors
- **Primary (CKB Red)**: `#c91a2b` - Used for CTAs, accents, and branding
- **Secondary (Blue)**: `#2196F3` - Used for secondary actions and info
- **Success (Green)**: `#4CAF50` - Used for form submissions and success states
- **Font**: Inter (Google Fonts) - Modern, clean sans-serif

#### Theme Toggle Implementation
Each Streamlit page must include theme support:

**Main Page (Attendance.py):**
```python
from pathlib import Path

# Initialize theme in session state
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Function to load CSS files
def load_css():
    """Load custom CSS files for styling"""
    css_files = [
        "assets/style.css",
        "assets/dark-theme.css" if st.session_state.get("theme", "dark") == "dark" 
        else "assets/light-theme.css",
    ]
    
    css_content = ""
    for css_file in css_files:
        css_path = Path(__file__).parent / css_file
        if css_path.exists():
            with open(css_path) as f:
                css_content += f.read()
    
    # Apply theme data attribute to root
    theme = st.session_state.get("theme", "dark")
    css_content = f"""
    <style>
    :root {{
        data-theme: "{theme}";
    }}
    {css_content}
    </style>
    """
    
    st.markdown(css_content, unsafe_allow_html=True)

# Load CSS
load_css()

# Theme toggle in sidebar (main page only)
with st.sidebar:
    current_theme = st.session_state.get("theme", "dark")
    if st.button("🌙" if current_theme == "dark" else "☀️", key="theme_toggle"):
        st.session_state.theme = "light" if current_theme == "dark" else "dark"
        st.rerun()
```

**Subpages (pages/2_Analytics.py, pages/3_Settings.py):**
```python
# For pages in pages/ directory, adjust path by going up one level
css_path = Path(__file__).parent.parent / css_file
```

### CSS Variable System
Use CSS variables defined in `assets/style.css` for consistent theming:

#### Spacing
- `--spacing-xs`: 4px
- `--spacing-sm`: 8px
- `--spacing-md`: 16px
- `--spacing-lg`: 24px
- `--spacing-xl`: 32px
- `--spacing-2xl`: 48px

#### Border Radius
- `--radius-sm`: 4px
- `--radius-md`: 8px
- `--radius-lg`: 12px
- `--radius-xl`: 16px
- `--radius-full`: 9999px

#### Transitions
- `--transition-fast`: 150ms (hover effects)
- `--transition-base`: 250ms (standard animations)
- `--transition-slow`: 350ms (page transitions)

#### Theme-Specific Colors
Colors are defined per theme and automatically applied via CSS variables:
- `--primary-color`, `--secondary-color`, `--success-color`
- `--bg-primary`, `--bg-secondary`, `--bg-tertiary`
- `--text-primary`, `--text-secondary`, `--text-tertiary`
- `--border-color`, `--border-hover`
- `--card-background`, `--card-border`, `--card-hover-background`
- `--input-background`, `--input-border`, `--input-focus-ring`

### Component Styling Guidelines

#### Buttons
Streamlit buttons automatically styled with these variants:

**Primary Button (Red)** - Use for main CTAs:
```python
# Styled with red gradient (#c91a2b → #a01523)
# Hover: Lifts up, enhanced glow effect
# Click: Ripple animation
```

**Secondary Button (Blue)** - Use for alternative actions:
```python
# Styled with blue gradient (#2196F3 → #1976D2)
```

**Form Submit Button (Green)** - Automatic for form submissions:
```python
with st.form("example_form"):
    # ... form fields
    st.form_submit_button("Submit")  # Green gradient (#4CAF50 → #388E3C)
```

**Default Buttons** - Theme-aware styling:
```python
st.button("Click Me")  # Uses theme background/border colors
```

**Button Effects:**
- Hover: `translateY(-2px)` lift effect
- Click: Ripple animation (expanding circle)
- All: `var(--transition-fast)` smooth transitions

#### Form Inputs
All input fields are automatically styled:
- **Background**: Glassmorphism effect with theme colors
- **Border**: 2px solid, theme-aware
- **Focus State**: Primary color border + 3px focus ring
- **Transition**: Smooth border/shadow transitions

```python
# All these get automatic styling:
st.text_input("Name")
st.text_area("Comments")
st.selectbox("Rank", options)
st.date_input("Date")
st.file_uploader("Upload")
```

#### Cards & Containers
Metric cards and containers have glassmorphism effects:
```python
st.metric("Total Points", "150")  # Auto-styled with glass background
```

**Card Effects:**
- Background: Semi-transparent with backdrop blur
- Hover: Enhanced shadow + slight lift
- Border: 1px solid with theme color

#### Data Display

**DataFrames:**
```python
st.dataframe(df)  # Auto-styled with:
# - Header background with bold text
# - Alternating row colors
# - Hover highlight
# - Rounded corners
```

**Plotly Charts:**
Use the theme helper function for consistent chart styling:
```python
def get_chart_theme():
    """Get Plotly template based on current theme"""
    theme = st.session_state.get("theme", "dark")
    if theme == "dark":
        return {
            "template": "plotly_dark",
            "colors": ["#c91a2b", "#2196F3", "#4CAF50", "#FFA726", "#9C27B0"],
            "paper_bgcolor": "rgba(25, 27, 31, 0.8)",
            "plot_bgcolor": "rgba(15, 17, 21, 0.5)",
            "font_color": "#FFFFFF"
        }
    else:
        return {
            "template": "plotly_white",
            "colors": ["#c91a2b", "#1976D2", "#388E3C", "#F57C00", "#7B1FA2"],
            "paper_bgcolor": "rgba(255, 255, 255, 0.9)",
            "plot_bgcolor": "rgba(245, 245, 245, 0.5)",
            "font_color": "#212121"
        }

# Apply to charts:
theme = get_chart_theme()
fig = px.bar(df, template=theme["template"], color_discrete_sequence=theme["colors"])
```

#### Alerts & Notifications

**Streamlit Alerts** - Automatically styled with colored borders:
```python
st.success("Success message")  # Green left border
st.warning("Warning message")  # Orange left border
st.error("Error message")      # Red left border
st.info("Info message")        # Blue left border
```

**Toast Notifications:**
```python
st.toast("Member checked in!", icon="✅")  # Slide-in animation from right
```

### Glassmorphism Effects
The UI uses glassmorphism (frosted glass effect) extensively:
- **Sidebar**: Semi-transparent with 16px backdrop blur
- **Cards**: Glass background with border
- **Containers**: Layered transparency for depth

Elements with glassmorphism automatically have:
- `backdrop-filter: blur(16px)`
- Semi-transparent background (rgba)
- 1px border with theme color
- Smooth transitions on hover

### Animation Guidelines

**Built-in Animations:**
- **fadeIn**: Page content on load (350ms)
- **slideInRight**: Toast notifications (250ms)
- **scaleIn**: Modal/popup appearances
- **pulse**: Loading states

**Hover Effects:**
- Buttons/Cards: Lift up 2px
- Interactive elements: Enhanced shadow
- All: Smooth cubic-bezier easing

### Responsive Design
Mobile breakpoint at 768px automatically adjusts:
- Reduced spacing/padding
- Smaller font sizes (h1: 3xl → 2xl)
- Compact button sizing
- Stack columns vertically

No manual media queries needed - the CSS handles it.

### Accessibility Standards

**Color Contrast:**
- Dark theme: White text on dark backgrounds (high contrast)
- Light theme: Dark text on light backgrounds (high contrast)
- All meet WCAG AA standard (4.5:1 for body text)

**Interactive Elements:**
- All buttons have visible focus states
- Form inputs show focus ring
- Hover states provide clear visual feedback

**Semantic Colors:**
- Red: Errors, danger, primary actions
- Green: Success, completion
- Blue: Information, secondary actions
- Orange: Warnings, caution

### Adding New Streamlit Pages
When creating new pages:

1. **Copy CSS Loading Function** from existing pages
2. **Adjust Path** if in subdirectory: `Path(__file__).parent.parent / css_file`
3. **Initialize Theme State**: `if "theme" not in st.session_state: st.session_state.theme = "dark"`
4. **Load CSS Early**: Call `load_css()` before any UI elements
5. **Use Plotly Theme Helper**: For consistent chart styling

### Modifying Styles
To customize the UI:

**Global Changes** → Edit `assets/style.css`:
- Spacing, transitions, shadows
- Component base styles
- Animations

**Theme Colors** → Edit theme files:
- `assets/dark-theme.css` for dark mode colors
- `assets/light-theme.css` for light mode colors

**Never modify** `.streamlit/config.toml` colors directly - use CSS variables instead for theme switching to work.

### Best Practices

1. **Always use CSS variables** for colors/spacing instead of hardcoded values
2. **Test both themes** when making style changes
3. **Maintain glassmorphism** - use semi-transparent backgrounds with blur
4. **Keep animations smooth** - use provided transition variables
5. **Respect hover states** - all interactive elements should have visual feedback
6. **Mobile-first mindset** - ensure layouts work on small screens
7. **Consistent spacing** - use spacing variables, not arbitrary pixel values
8. **Theme persistence** - session state ensures theme survives page navigation
