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

### Key Constraints
- `FactAttendance`: Unique constraint on (user_uuid, class_id, attendance_date)
- `ClassInstance`: Unique constraint on (class_id, class_date)
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
