# Codebase Structure

**Analysis Date:** 2026-02-11

## Directory Layout

```
ckb_tracker/
├── app/                    # FastAPI backend application
│   ├── routers/           # API endpoint modules (one per entity)
│   ├── services/          # External service integrations
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point
│   ├── models.py          # SQLAlchemy database models
│   ├── schemas.py         # Pydantic validation schemas
│   ├── database.py        # Database connection & session
│   ├── auth.py            # JWT & password hashing
│   ├── config.py          # Configuration from environment
│   ├── db_helpers.py      # Common database queries
│   └── constants.py       # Application constants
├── pages/                 # Streamlit additional pages (auto-routed)
│   ├── 2_Analytics.py     # Analytics dashboard
│   ├── 3_Settings.py      # Admin settings console
│   ├── 4_Teacher.py       # Teacher dashboard (JWT protected)
│   └── 5_Student_Analytics.py # Student analytics view
├── assets/                # Frontend styling resources
│   ├── style.css          # Component styles
│   ├── dark-theme.css     # Dark mode palette
│   └── light-theme.css    # Light mode palette
├── static/                # Static file serving
│   └── profile_pics/      # Local photo storage (legacy)
├── tests/                 # Pytest test suite
│   ├── test_*.py          # Test modules
│   └── __init__.py
├── utils/                 # Shared utilities
│   ├── api_client.py      # HTTP client for frontend
│   └── __init__.py
├── .streamlit/            # Streamlit configuration
├── .venv/                 # Python virtual environment
├── Attendance.py          # Main Streamlit page (entry point)
├── pyproject.toml         # Python dependencies
├── test.db                # SQLite database file
├── reset_db.py            # Database schema reset script
├── seed_complete_data.py  # Comprehensive data seeder
├── seed_users.py          # Basic user seeder
├── seed_simple.py         # Minimal data seeder
├── AGENTS.md              # AI development guide
└── README.md              # User documentation
```

## Directory Purposes

**app/**
- Purpose: Backend API application code
- Contains: FastAPI app, models, routers, services
- Key files: `main.py` (app initialization), `models.py` (database schema), `schemas.py` (API contracts)

**app/routers/**
- Purpose: API endpoint implementations organized by entity
- Contains: One router file per major entity (users, classes, attendance, etc.)
- Key files: `users.py` (user CRUD + photos), `attendance.py` (check-in logic), `auth.py` (login/session), `class_instances.py` (lesson assignments), `curricula.py` + `lessons.py` (curriculum management), `feedback.py` (student feedback)

**app/services/**
- Purpose: External service integrations
- Contains: Cloudinary photo upload service
- Key files: `cloudinary_service.py` (photo upload/delete operations)

**pages/**
- Purpose: Additional Streamlit pages (numbered for navigation order)
- Contains: Analytics, settings, teacher dashboard, student views
- Key files: `2_Analytics.py` (charts and metrics), `3_Settings.py` (admin console), `4_Teacher.py` (JWT-protected teacher tools)

**assets/**
- Purpose: CSS styling for Streamlit frontend
- Contains: Theme-aware stylesheets
- Key files: `style.css` (main component styles), `dark-theme.css` + `light-theme.css` (color palettes)

**static/**
- Purpose: Static file serving via FastAPI
- Contains: Profile pictures (legacy local storage)
- Key files: `profile_pics/` directory mounted at `/static` endpoint

**tests/**
- Purpose: Pytest test suite
- Contains: Unit and integration tests
- Key files: `test_smoke.py` (basic tests), `test_curricula.py` + `test_lessons.py` (curriculum tests), `test_role_system.py` (role management), `test_class_instances.py` (lesson assignment)

**utils/**
- Purpose: Shared utility code
- Contains: API client abstraction for frontend
- Key files: `api_client.py` (CKBAPIClient class with typed methods)

## Key File Locations

**Entry Points:**
- `Attendance.py`: Main Streamlit page - attendance tracking and user creation
- `app/main.py`: FastAPI application initialization and router registration

**Configuration:**
- `app/config.py`: Settings class with environment variable loading
- `.env`: Environment variables (secrets, API keys) - gitignored
- `.env.example`: Template for required environment variables
- `pyproject.toml`: Python dependencies and project metadata

**Core Logic:**
- `app/models.py`: SQLAlchemy ORM models (14 entities including User, FactAttendance, ClassInstance, Curriculum, Lesson)
- `app/schemas.py`: Pydantic validation schemas (505 lines, ~40 schemas)
- `app/database.py`: Database engine and session factory
- `app/auth.py`: JWT token management and password hashing (Argon2)

**Testing:**
- `tests/test_smoke.py`: Basic smoke tests
- `tests/test_scd_constraint_fix.py`: SCD Type 2 constraint validation
- `tests/test_curricula.py`: Curriculum CRUD operations (14 tests)
- `tests/test_lessons.py`: Lesson management (16 tests)
- `tests/test_curriculum_integration.py`: End-to-end curriculum workflow (8 tests)
- `tests/test_role_system.py`: Role assignment and history
- `tests/test_teacher_assignment.py`: Teacher assignment to classes

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `class_instances.py`, `db_helpers.py`)
- Streamlit pages: `{number}_{Title}.py` (e.g., `2_Analytics.py`, `4_Teacher.py`)
- Test files: `test_{feature}.py` (e.g., `test_lessons.py`)
- Database files: `{descriptor}.db` (e.g., `test.db`, `test_curricula.db`)

**Directories:**
- All lowercase `snake_case` (e.g., `app/routers/`, `static/profile_pics/`)

**Python Classes:**
- Models: `PascalCase` (e.g., `User`, `FactAttendance`, `ClassInstance`)
- Schemas: `PascalCase` + suffix (e.g., `UserCreate`, `UserResponse`, `AttendanceCreate`)
- Exceptions: Standard Python exception names

**Python Functions/Variables:**
- Functions: `snake_case` (e.g., `get_users()`, `record_attendance()`)
- Variables: `snake_case` (e.g., `user_uuid`, `class_id`, `attendance_date`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`)

**Database Tables:**
- Table names: `snake_case` via `__tablename__` (e.g., `users`, `attendance`, `class_instances`, `term_targets`)
- Column names: `snake_case` (e.g., `user_uuid`, `is_current`, `effective_date`)
- Constraint names: descriptive with underscores (e.g., `_user_class_date_uc`, `uix_user_current`)

**API Endpoints:**
- Plural nouns: `/users/`, `/classes/`, `/attendance/`
- Nested resources: `/attendance/user/{user_uuid}`, `/term-targets/term/{term_id}`
- Actions: `/auth/teacher-login`, `/roles/user/{uuid}/history`

## Where to Add New Code

**New API Endpoint:**
- Primary code: `app/routers/{entity}.py` (create new file if new entity)
- Schema: Add to `app/schemas.py` (Create/Update/Response schemas)
- Model: Add to `app/models.py` if new database table needed
- Registration: Add router import and include in `app/main.py`
- Tests: `tests/test_{entity}.py`

**New Database Model:**
- Implementation: `app/models.py` (inherit from `Base`)
- Schema: `app/schemas.py` (corresponding Pydantic models)
- Migration: Run `reset_db.py` to recreate tables (no migration framework currently)
- Seeding: Update `seed_complete_data.py` with sample data
- Tests: `tests/test_{entity}.py`

**New Streamlit Page:**
- Primary code: `pages/{number}_{Title}.py` (number determines navigation order)
- Styling: Reuse `assets/style.css` theme loader pattern
- API calls: Use `utils/api_client.py` methods or direct requests
- State: Use `st.session_state` for page-specific data

**New External Service:**
- Implementation: `app/services/{service_name}_service.py`
- Configuration: Add settings to `app/config.py`
- Environment vars: Document in `.env.example`
- Usage: Import in routers that need the service
- Tests: `tests/test_{service_name}.py`

**New Feature (Full Stack):**
1. Database model: `app/models.py`
2. Pydantic schemas: `app/schemas.py`
3. API router: `app/routers/{entity}.py`
4. Register router: `app/main.py`
5. Frontend UI: `pages/{N}_{Name}.py` or add to existing page
6. Tests: `tests/test_{entity}.py`
7. Seed data: `seed_complete_data.py`

## Special Directories

**.venv/**
- Purpose: Python virtual environment for dependencies
- Generated: `python -m venv .venv`
- Committed: No (gitignored)

**.streamlit/**
- Purpose: Streamlit configuration files
- Generated: Automatically by Streamlit
- Committed: Yes (project-specific config)

**__pycache__/**
- Purpose: Python bytecode cache
- Generated: Automatically by Python interpreter
- Committed: No (gitignored)

**.planning/**
- Purpose: AI-generated codebase documentation and plans
- Generated: By GSD commands (`/gsd-map-codebase`, `/gsd-plan-phase`)
- Committed: Yes (source of truth for AI context)
- Contains: `codebase/` (this file and related docs)

**static/profile_pics/**
- Purpose: Local fallback for profile photos (legacy)
- Generated: During photo upload if Cloudinary unavailable
- Committed: No (gitignored, user-generated content)
- Note: Cloudinary is primary storage method now

## Import Organization Pattern

**Standard Order:**
1. Standard library imports (e.g., `import os`, `from datetime import datetime`)
2. Third-party imports (e.g., `from fastapi import APIRouter`, `from sqlalchemy.orm import Session`)
3. Local imports (e.g., `from .. import models`, `from app import schemas`)

**Example from `app/routers/users.py`:**
```python
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_password_hash
from ..services.cloudinary_service import cloudinary_service
```

## File Size Reference

**Largest Files (by line count):**
- `app/schemas.py`: 505 lines (Pydantic schemas)
- `app/routers/users.py`: 414 lines (user CRUD + photo management)
- `app/models.py`: 342 lines (14 database models)
- `app/routers/attendance.py`: 300+ lines (attendance logic + analytics)

**Typical Router Size:** 100-250 lines per entity

**Test Files:** 50-200 lines per test module

---

*Structure analysis: 2026-02-11*
