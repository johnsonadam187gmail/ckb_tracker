# Testing Patterns

**Analysis Date:** 2026-02-11

## Test Framework

**Runner:**
- pytest (detected via test file imports)
- No explicit `pytest.ini` or configuration file in root
- Configuration likely via `pyproject.toml` or defaults

**Assertion Library:**
- pytest built-in assertions (standard `assert` statements)
- No third-party assertion libraries (e.g., assertpy, expects)

**Run Commands:**
```bash
pytest                           # Run all tests
pytest -v                        # Verbose mode
pytest tests/test_smoke.py       # Run specific file
pytest tests/test_smoke.py::test_root_endpoint  # Run specific test
pytest --cov=app tests/          # Run with coverage (requires pytest-cov)
```

## Test File Organization

**Location:**
- All tests in dedicated `tests/` directory (separate from source)
- No co-located tests (no `test_*.py` files in `app/` directory)

**Naming:**
- Pattern: `test_*.py` (pytest standard)
- Descriptive names: `test_smoke.py`, `test_role_system.py`, `test_curricula.py`, `test_class_instances.py`
- Feature-specific names: `test_teacher_assignment.py`, `test_curriculum_integration.py`
- Total test files: 11 files

**Structure:**
```
tests/
├── __init__.py               # Empty package marker
├── test_smoke.py             # Basic endpoint smoke tests
├── test_role_system.py       # Role management unit/integration tests
├── test_curricula.py         # Curriculum CRUD endpoint tests
├── test_lessons.py           # Lesson CRUD endpoint tests
├── test_curriculum_integration.py  # Full workflow integration tests
├── test_class_instances.py   # ClassInstance endpoint tests
├── test_teacher_assignment.py     # Teacher assignment feature tests
├── test_teacher_dashboard_endpoint.py  # Teacher dashboard tests
├── test_points.py            # Points calculation tests
└── test_scd_constraint_fix.py     # SCD Type 2 constraint tests
```

## Test Structure

**Suite Organization:**

**Style 1: Simple smoke tests (test_smoke.py):**
```python
"""
Basic smoke tests to ensure critical functionality works.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test that the root endpoint returns a response."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_get_users_endpoint():
    """Test that the users endpoint is accessible."""
    response = client.get("/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Style 2: Unit tests with fixtures (test_role_system.py):**
```python
"""
Unit and integration tests for role system.
Run with: pytest tests/test_role_system.py -v
"""

import pytest
from datetime import datetime, timezone, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app import models
from app.database import Base


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()

    # Seed roles
    roles = [
        models.Role(name="Student", description="Member attending classes"),
        models.Role(name="Teacher", description="Instructor teaching classes"),
        models.Role(name="Admin", description="Administrator with full access"),
    ]
    for role in roles:
        db.add(role)
    db.commit()

    yield db

    db.close()


def test_role_creation(test_db):
    """Test that roles are created correctly"""
    roles = test_db.query(models.Role).all()
    assert len(roles) == 3
    assert {r.name for r in roles} == {"Student", "Teacher", "Admin"}
```

**Style 3: API integration tests with dependency override (test_curricula.py):**
```python
"""Tests for curriculum management endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app import models

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_curricula.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_class(setup_database):
    """Create a sample class for testing."""
    db = TestingSessionLocal()
    class_schedule = models.ClassSchedule(
        class_uuid="test-class-uuid",
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        gym_id=1,
        class_type_id=1,
        is_current=True,
    )
    db.add(class_schedule)
    db.commit()
    db.refresh(class_schedule)
    class_id = class_schedule.id
    db.close()
    return class_id


def test_create_curriculum_success(sample_class):
    """Test creating a curriculum for a class."""
    payload = {
        "class_id": sample_class,
        "name": "Fundamentals 1 Curriculum",
        "description": "Core techniques for beginners",
    }

    response = client.post("/curricula/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["class_id"] == sample_class
    assert data["name"] == "Fundamentals 1 Curriculum"
    assert data["description"] == "Core techniques for beginners"
    assert "id" in data
```

**Patterns:**
- **Docstrings:** Every test function has docstring describing what it tests
- **Module docstrings:** Test files include module-level docstrings with purpose
- **Descriptive names:** Test function names clearly describe what they test
- **Setup/Teardown:** Fixtures handle setup, `yield` for teardown
- **Assertions:** Multiple assertions per test when testing related properties

## Mocking

**Framework:** None detected

**Database Strategy:**
- Use in-memory SQLite databases for tests (`:memory:` or temporary files)
- FastAPI dependency override pattern for test database injection
- No external mocking library (unittest.mock, pytest-mock) detected

**Patterns:**

**In-Memory Database (Unit Tests):**
```python
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    
    # Seed test data if needed
    
    yield db
    
    db.close()
```

**Test Database with Dependency Override (API Tests):**
```python
# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_curricula.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override FastAPI dependency
app.dependency_overrides[get_db] = override_get_db

# Create TestClient
client = TestClient(app)
```

**What to Mock:**
- Database connections (overridden with test databases, not mocked)
- External services (Cloudinary) - not mocked in current tests, likely tested manually

**What NOT to Mock:**
- SQLAlchemy models (use real models with test database)
- Business logic (test actual implementation)
- FastAPI routing (use TestClient to test actual routes)

## Fixtures and Factories

**Test Data:**

**Database Seeding Pattern:**
```python
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()

    # Seed roles (required for many tests)
    roles = [
        models.Role(name="Student", description="Member attending classes"),
        models.Role(name="Teacher", description="Instructor teaching classes"),
        models.Role(name="Admin", description="Administrator with full access"),
    ]
    for role in roles:
        db.add(role)
    db.commit()

    yield db

    db.close()
```

**Test Data Factory Pattern:**
```python
@pytest.fixture
def sample_class(setup_database):
    """Create a sample class for testing."""
    db = TestingSessionLocal()
    class_schedule = models.ClassSchedule(
        class_uuid="test-class-uuid",
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        gym_id=1,
        class_type_id=1,
        is_current=True,
    )
    db.add(class_schedule)
    db.commit()
    db.refresh(class_schedule)
    class_id = class_schedule.id
    db.close()
    return class_id


@pytest.fixture
def sample_curriculum(setup_database):
    """Create a sample curriculum for testing."""
    db = TestingSessionLocal()

    # Create class first
    class_schedule = models.ClassSchedule(
        class_uuid="test-class-uuid",
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        gym_id=1,
        class_type_id=1,
        is_current=True,
    )
    db.add(class_schedule)
    db.commit()
    db.refresh(class_schedule)

    # Create curriculum
    curriculum = models.Curriculum(
        class_id=class_schedule.id,
        name="Test Curriculum",
        description="Test description",
    )
    db.add(curriculum)
    db.commit()
    db.refresh(curriculum)
    curriculum_id = curriculum.id
    db.close()
    return curriculum_id
```

**Location:**
- Fixtures defined in same test file (no shared `conftest.py` detected)
- Each test module contains its own fixtures
- Future: Consider creating `tests/conftest.py` for shared fixtures

**Patterns:**
- Fixtures create test data, return IDs or objects
- `autouse=True` for automatic database setup/teardown
- `scope="function"` for per-test isolation (default)
- Use `db.refresh()` after commit to get generated IDs
- Close database session in fixture teardown

## Coverage

**Requirements:** Not specified

**Tool:**
- pytest-cov (mentioned in run commands, not explicitly configured)
- No `.coveragerc` or coverage configuration file detected

**View Coverage:**
```bash
pytest --cov=app tests/
pytest --cov=app --cov-report=html tests/  # Generate HTML report
pytest --cov=app --cov-report=term-missing tests/  # Show missing lines
```

**Current State:**
- No coverage badges or reports in repository
- No CI/CD integration detected
- Coverage tracking manual via pytest-cov

## Test Types

**Unit Tests:**
- Scope: Individual models, functions, business logic
- Examples: `test_role_system.py` (database model operations)
- Approach: Use in-memory SQLite database, test model creation/updates/queries
- Total unit tests: ~20-30 (estimated from `test_role_system.py`)

**Integration Tests:**
- Scope: API endpoints with database interactions
- Examples: `test_curricula.py`, `test_lessons.py`, `test_class_instances.py`
- Approach: Use TestClient with overridden database dependency
- Total integration tests: ~50-60 (estimated across multiple files)

**E2E Tests:**
- Framework: Not implemented
- Current state: Manual testing via Streamlit UI
- Future: Consider adding E2E tests with Selenium or Playwright for UI

**Smoke Tests:**
- Scope: Basic health checks for all major endpoints
- File: `tests/test_smoke.py`
- Purpose: Ensure critical endpoints are accessible and return expected types
- Total smoke tests: 8 tests covering GET endpoints

## Common Patterns

**Async Testing:**
- Not used (FastAPI endpoints are synchronous in this project)
- No `async def` functions in tests
- No `pytest-asyncio` imports detected

**API Testing Pattern:**
```python
def test_create_curriculum_success(sample_class):
    """Test creating a curriculum for a class."""
    payload = {
        "class_id": sample_class,
        "name": "Fundamentals 1 Curriculum",
        "description": "Core techniques for beginners",
    }

    response = client.post("/curricula/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["class_id"] == sample_class
    assert data["name"] == "Fundamentals 1 Curriculum"
    assert "id" in data
```

**Error Testing:**
```python
def test_create_curriculum_duplicate(sample_class):
    """Test that duplicate curricula for same class are rejected."""
    payload = {
        "class_id": sample_class,
        "name": "First Curriculum",
    }

    # Create first curriculum
    response1 = client.post("/curricula/", json=payload)
    assert response1.status_code == 200

    # Try to create second curriculum for same class
    response2 = client.post("/curricula/", json=payload)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()


def test_get_curriculum_by_id_not_found():
    """Test retrieving non-existent curriculum."""
    response = client.get("/curricula/99999")

    assert response.status_code == 404
```

**Database Testing Pattern:**
```python
def test_attendance_with_teacher(test_db):
    """Test that attendance records can store teacher information"""
    # Create student and teacher
    student_uuid = str(uuid.uuid4())
    teacher_uuid = str(uuid.uuid4())

    student = models.User(
        user_uuid=student_uuid,
        first_name="Student",
        last_name="One",
        email="student@example.com",
        rank="White",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    
    teacher = models.User(
        user_uuid=teacher_uuid,
        first_name="Teacher",
        last_name="One",
        email="teacher@example.com",
        rank="Black",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )

    test_db.add_all([student, teacher])
    test_db.commit()
    
    # Create attendance with teacher
    attendance = models.FactAttendance(
        user_uuid=student_uuid,
        class_id=class_schedule.id,
        attendance_date=date.today(),
        teacher_uuid=teacher_uuid,
        user_role_id=student_ur.id,
    )
    test_db.add(attendance)
    test_db.commit()

    # Verify
    saved_attendance = test_db.query(models.FactAttendance).first()
    assert saved_attendance.user_uuid == student_uuid
    assert saved_attendance.teacher_uuid == teacher_uuid
    assert saved_attendance.teacher.first_name == "Teacher"
```

**Test Documentation Pattern:**
```python
# File-level docstring
"""
Unit and integration tests for role system.
Run with: pytest tests/test_role_system.py -v
"""

# Test function docstrings
def test_multiple_roles_assignment(test_db):
    """Test that a user can have multiple roles simultaneously"""
    # Test implementation
```

**Assertion Patterns:**
- Status code assertions: `assert response.status_code == 200`
- Response structure: `assert "id" in data`
- Type checking: `assert isinstance(response.json(), list)`
- Content verification: `assert data["name"] == "Expected Name"`
- Partial match: `assert "expected" in response.json()["detail"].lower()`
- Set comparisons: `assert {r.name for r in roles} == {"Student", "Teacher", "Admin"}`
- Count assertions: `assert len(data) == 2`

**Total Test Count:**
- 82+ test functions across 11 test files
- Coverage includes: CRUD operations, role system, attendance tracking, curriculum management, SCD Type 2 versioning, error cases

---

*Testing analysis: 2026-02-11*
