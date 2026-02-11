# Architecture

**Analysis Date:** 2026-02-11

## Pattern Overview

**Overall:** Three-tier web application with API-first design

**Key Characteristics:**
- Decoupled backend (FastAPI) and frontend (Streamlit)
- RESTful API as the integration layer
- Database-first design with SQLAlchemy ORM
- Slowly Changing Dimensions (SCD Type 2) for historical tracking
- Modular router-based API organization

## Layers

**Data Layer:**
- Purpose: Persistence and data modeling
- Location: `app/models.py`, `app/database.py`
- Contains: SQLAlchemy models, database engine, session management
- Depends on: SQLite database (`test.db`)
- Used by: All API routers and services
- Pattern: Active Record with declarative base, connection pooling via SessionLocal

**API Layer:**
- Purpose: Business logic and HTTP request handling
- Location: `app/routers/`, `app/main.py`
- Contains: FastAPI routers, endpoint definitions, request validation
- Depends on: Data layer (via dependency injection), Pydantic schemas
- Used by: Frontend layer via HTTP
- Pattern: Router-per-entity, dependency injection for database sessions

**Presentation Layer:**
- Purpose: User interface and visualization
- Location: `Attendance.py`, `pages/`
- Contains: Streamlit pages, charts, forms, user interactions
- Depends on: API layer via HTTP requests, utility client
- Used by: End users
- Pattern: Multi-page Streamlit app with session state management

**Service Layer:**
- Purpose: External integrations and cross-cutting concerns
- Location: `app/services/`, `app/auth.py`, `app/config.py`
- Contains: Cloudinary photo service, JWT authentication, password hashing
- Depends on: Environment configuration, third-party libraries
- Used by: API layer routers
- Pattern: Singleton service instances, configuration-driven

**Validation Layer:**
- Purpose: Request/response data validation and serialization
- Location: `app/schemas.py`
- Contains: Pydantic models for API contracts
- Depends on: Pydantic v2
- Used by: API layer for request parsing and response formatting
- Pattern: Schema-per-entity with inheritance (Base/Create/Update/Response)

## Data Flow

**Attendance Check-In Flow:**

1. User selects member and clicks "Check In" in `Attendance.py`
2. Frontend makes POST request to `/attendance/` with form data
3. `app/routers/attendance.py` receives request via FastAPI
4. Router validates data using `AttendanceCreate` schema
5. Router queries/creates `ClassInstance` for (class_id, date) tuple
6. Router creates `FactAttendance` record linked to ClassInstance
7. Database session commits transaction with unique constraint validation
8. Response serialized via `AttendanceResponse` schema
9. Frontend displays success toast or error message

**User Analytics Flow:**

1. `pages/2_Analytics.py` fetches user list via GET `/users/`
2. User selects member from dropdown
3. Frontend requests GET `/attendance/user/{user_uuid}`
4. Router executes join query across User, ClassSchedule, FactAttendance
5. Results enriched with computed fields (points, teacher names)
6. Response serialized as list of `UserAnalyticsResponse`
7. Frontend processes data into pandas DataFrame
8. Plotly charts render from DataFrame aggregations

**SCD Type 2 Update Flow:**

1. Admin updates user via Settings page
2. Frontend sends PUT `/users/{user_uuid}` with updated fields
3. Router queries current User record (is_current=True)
4. Router expires old record (is_current=False, end_date=now)
5. Router creates new User record (same user_uuid, is_current=True, new data)
6. Database commits both updates atomically
7. Composite unique constraint (user_uuid, is_current) enforces one current version
8. Historical versions preserved for audit trail

**State Management:**
- Frontend: Streamlit session_state for UI state, JWT tokens, theme preferences
- Backend: Stateless API, all state in database or JWT claims
- Database: SCD Type 2 for temporal state (users, classes, roles)

## Key Abstractions

**SCD Type 2 Versioning:**
- Purpose: Track historical changes to entities over time
- Examples: `app/models.py` User, ClassSchedule, UserRole
- Pattern: UUID anchor (user_uuid, class_uuid) + version fields (is_current, effective_date, end_date)
- Implementation: Composite unique constraints, update creates new version instead of modifying

**Fact Table Pattern:**
- Purpose: Immutable event records for analytics
- Examples: `app/models.py` FactAttendance
- Pattern: Foreign keys to dimension tables (User, ClassSchedule), date fields, no updates after creation
- Implementation: Unique constraints prevent duplicate attendance, relationships via UUIDs

**Router Modules:**
- Purpose: Organize API endpoints by domain entity
- Examples: `app/routers/users.py`, `app/routers/attendance.py`, `app/routers/classes.py`
- Pattern: APIRouter with prefix and tags, included in main app
- Implementation: Dependency injection for database sessions via `get_db()`

**Schema Hierarchy:**
- Purpose: Type-safe API contracts with validation
- Examples: UserCreate, UserResponse, UserUpdate in `app/schemas.py`
- Pattern: Base schema with common fields, specialized schemas for operations
- Implementation: Pydantic BaseModel with Config.from_attributes for ORM compatibility

**JWT Authentication:**
- Purpose: Stateless session management for teachers
- Examples: `app/auth.py` token creation/verification
- Pattern: 5-minute expiry with rolling window extension on activity
- Implementation: jose JWT library, Argon2 password hashing via passlib

**Curriculum Management:**
- Purpose: Organize lessons into structured learning paths
- Examples: `app/models.py` Curriculum, Lesson, ClassInstance relationships
- Pattern: One Curriculum per ClassSchedule (1:1), many Lessons per Curriculum (1:N), Lessons assigned to ClassInstances (N:1)
- Implementation: Foreign key relationships with cascade deletes, unique constraint on Curriculum.class_id

## Entry Points

**Backend (API):**
- Location: `app/main.py`
- Triggers: `uvicorn app.main:app --reload` (port 8000)
- Responsibilities: Initialize FastAPI app, create database tables, mount routers, serve static files
- Key Code: Lines 27-48 register all routers and mount `/static` directory

**Frontend (UI):**
- Location: `Attendance.py`
- Triggers: `streamlit run Attendance.py` (port 8501)
- Responsibilities: Main attendance page, user creation form, daily check-ins, theme toggle
- Key Code: Lines 161-321 handle member creation form and attendance recording

**Additional Pages:**
- `pages/2_Analytics.py`: Student/teacher analytics dashboards with charts
- `pages/3_Settings.py`: Admin console for managing users, classes, roles, curricula, lessons
- `pages/4_Teacher.py`: Teacher dashboard with JWT authentication, class roster, lesson display
- `pages/5_Student_Analytics.py`: Student-specific analytics view

**Database Initialization:**
- Location: `reset_db.py`
- Triggers: Manual execution `python reset_db.py`
- Responsibilities: Drop all tables and recreate schema
- Note: Destructive operation for development

**Data Seeding:**
- Location: `seed_complete_data.py`
- Triggers: Manual execution `python seed_complete_data.py`
- Responsibilities: Populate database with realistic test data (users, classes, attendance, feedback)
- Note: Includes 10 users, 4 classes, 2 terms, attendance records

## Error Handling

**Strategy:** Exception-based with HTTP status codes

**Patterns:**
- SQLAlchemy IntegrityError → HTTPException 400 for constraint violations
- Database rollback on any exception in try/except blocks
- HTTPException with status_code and detail message for client errors
- Pydantic ValidationError automatically converted to 422 by FastAPI
- Frontend displays error messages via st.error() or st.warning()

**Examples:**
- Duplicate attendance check-in: IntegrityError caught → 400 "User is already checked into this class for today"
- Invalid UUID: 404 "User not found" from query.first() None check
- Missing required field: Pydantic raises 422 with field details
- Database connection failure: ConnectionError bubbles to frontend → st.error()

## Cross-Cutting Concerns

**Logging:** 
- Console output via print statements (development)
- No structured logging framework currently implemented
- Uvicorn access logs for HTTP requests
- Streamlit native logging for frontend errors

**Validation:** 
- Pydantic v2 schemas for all API requests/responses
- Field validators using `@field_validator` decorator (e.g., email normalization, rating values)
- Database constraints (unique, foreign key, not null) enforced at DB level
- Frontend validation in Streamlit forms (e.g., password length, required fields)

**Authentication:** 
- JWT tokens for teacher sessions (`app/auth.py`)
- Argon2 password hashing via passlib (`app/auth.py`)
- Session verification endpoint with rolling expiry
- Role-based access checks (Teacher role required for dashboard)
- No authentication for student attendance or analytics (open access)

**Configuration:**
- Environment variables loaded via python-dotenv
- `app/config.py` Settings class centralizes all configuration
- `.env` file for secrets (gitignored)
- `.env.example` template for required variables
- Auto-generation of SECRET_KEY if missing

**Photo Management:**
- Cloudinary service for cloud storage (`app/services/cloudinary_service.py`)
- Photo URLs stored in User.profile_image_url
- Local fallback directory: `static/profile_pics/` (legacy)
- SCD Type 2 versioning includes photo URL in historical records

**Database Session Management:**
- Dependency injection via `get_db()` generator
- Context manager pattern ensures session closure
- Auto-commit disabled, explicit commit in routers
- Rollback on exceptions

---

*Architecture analysis: 2026-02-11*
