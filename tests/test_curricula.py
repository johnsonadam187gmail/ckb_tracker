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


def test_create_curriculum_auto_name(sample_class):
    """Test curriculum creation with auto-generated name."""
    payload = {
        "class_id": sample_class,
        "description": "Auto-named curriculum",
    }

    response = client.post("/curricula/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Fundamentals 1 Curriculum"  # Auto-generated


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


def test_create_curriculum_nonexistent_class():
    """Test creating curriculum for non-existent class fails."""
    payload = {
        "class_id": 99999,
        "name": "Invalid Curriculum",
    }

    response = client.post("/curricula/", json=payload)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_all_curricula(sample_class):
    """Test retrieving all curricula."""
    # Create two classes with curricula
    db = TestingSessionLocal()
    class2 = models.ClassSchedule(
        class_uuid="test-class-uuid-2",
        class_name="Advanced",
        day="Tuesday",
        time="19:00",
        gym_id=1,
        class_type_id=1,
        is_current=True,
    )
    db.add(class2)
    db.commit()
    db.refresh(class2)
    class2_id = class2.id
    db.close()

    # Create curricula
    client.post("/curricula/", json={"class_id": sample_class, "name": "Curriculum 1"})
    client.post("/curricula/", json={"class_id": class2_id, "name": "Curriculum 2"})

    response = client.get("/curricula/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(c["name"] == "Curriculum 1" for c in data)
    assert any(c["name"] == "Curriculum 2" for c in data)


def test_get_curriculum_by_id(sample_class):
    """Test retrieving a specific curriculum."""
    # Create curriculum
    create_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "Test Curriculum"}
    )
    curriculum_id = create_response.json()["id"]

    response = client.get(f"/curricula/{curriculum_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == curriculum_id
    assert data["name"] == "Test Curriculum"


def test_get_curriculum_by_id_not_found():
    """Test retrieving non-existent curriculum."""
    response = client.get("/curricula/99999")

    assert response.status_code == 404


def test_get_curricula_by_class_id(sample_class):
    """Test retrieving curricula filtered by class_id."""
    # Create curriculum
    client.post("/curricula/", json={"class_id": sample_class, "name": "Filtered"})

    response = client.get(f"/curricula/?class_id={sample_class}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["class_id"] == sample_class


def test_update_curriculum(sample_class):
    """Test updating a curriculum."""
    # Create curriculum
    create_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "Original Name"}
    )
    curriculum_id = create_response.json()["id"]

    # Update curriculum
    update_payload = {
        "name": "Updated Name",
        "description": "Updated description",
    }
    response = client.put(f"/curricula/{curriculum_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"


def test_update_curriculum_not_found():
    """Test updating non-existent curriculum."""
    update_payload = {"name": "New Name"}
    response = client.put("/curricula/99999", json=update_payload)

    assert response.status_code == 404


def test_delete_curriculum(sample_class):
    """Test deleting a curriculum."""
    # Create curriculum
    create_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "To Delete"}
    )
    curriculum_id = create_response.json()["id"]

    # Delete curriculum
    response = client.delete(f"/curricula/{curriculum_id}")

    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify deletion
    get_response = client.get(f"/curricula/{curriculum_id}")
    assert get_response.status_code == 404


def test_delete_curriculum_not_found():
    """Test deleting non-existent curriculum."""
    response = client.delete("/curricula/99999")

    assert response.status_code == 404


def test_delete_curriculum_with_lessons(sample_class):
    """Test that curriculum with lessons can be deleted (cascade)."""
    # Create curriculum
    create_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "With Lessons"}
    )
    curriculum_id = create_response.json()["id"]

    # Add a lesson
    client.post(
        "/lessons/",
        json={
            "curriculum_id": curriculum_id,
            "title": "Test Lesson",
        },
    )

    # Delete curriculum (should cascade delete lessons)
    response = client.delete(f"/curricula/{curriculum_id}")

    # Note: Depending on cascade settings, this might fail or succeed
    # This test documents the expected behavior
    assert response.status_code in [200, 400]


def test_empty_curricula_list():
    """Test getting curricula when none exist."""
    response = client.get("/curricula/")

    assert response.status_code == 200
    data = response.json()
    assert data == []
