"""Tests for lesson management endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app import models

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_lessons.db"
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


def test_create_lesson_success(sample_curriculum):
    """Test creating a lesson in a curriculum."""
    payload = {
        "curriculum_id": sample_curriculum,
        "title": "Guard Passing Fundamentals",
        "description": "Learn basic guard passing techniques",
        "lesson_plan_url": "https://docs.google.com/document/d/abc123",
        "video_folder_url": "https://drive.google.com/drive/folders/xyz789",
    }

    response = client.post("/lessons/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["curriculum_id"] == sample_curriculum
    assert data["title"] == "Guard Passing Fundamentals"
    assert data["description"] == "Learn basic guard passing techniques"
    assert "docs.google.com" in data["lesson_plan_url"]
    assert "drive.google.com" in data["video_folder_url"]
    assert "id" in data


def test_create_lesson_minimal(sample_curriculum):
    """Test creating a lesson with only required fields."""
    payload = {
        "curriculum_id": sample_curriculum,
        "title": "Minimal Lesson",
    }

    response = client.post("/lessons/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Minimal Lesson"
    assert data["description"] is None
    assert data["lesson_plan_url"] is None
    assert data["video_folder_url"] is None


def test_create_lesson_nonexistent_curriculum():
    """Test creating lesson for non-existent curriculum fails."""
    payload = {
        "curriculum_id": 99999,
        "title": "Invalid Lesson",
    }

    response = client.post("/lessons/", json=payload)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_lesson_invalid_url(sample_curriculum):
    """Test that invalid URLs are rejected."""
    payload = {
        "curriculum_id": sample_curriculum,
        "title": "Lesson with Bad URL",
        "lesson_plan_url": "not-a-valid-url",
    }

    response = client.post("/lessons/", json=payload)

    # Pydantic validation should fail
    assert response.status_code == 422


def test_get_all_lessons(sample_curriculum):
    """Test retrieving all lessons."""
    # Create multiple lessons
    client.post(
        "/lessons/", json={"curriculum_id": sample_curriculum, "title": "Lesson 1"}
    )
    client.post(
        "/lessons/", json={"curriculum_id": sample_curriculum, "title": "Lesson 2"}
    )

    response = client.get("/lessons/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(lesson["title"] == "Lesson 1" for lesson in data)
    assert any(lesson["title"] == "Lesson 2" for lesson in data)


def test_get_lessons_by_curriculum_id(sample_curriculum):
    """Test filtering lessons by curriculum_id."""
    # Create lessons in the curriculum
    client.post(
        "/lessons/",
        json={"curriculum_id": sample_curriculum, "title": "Curriculum Lesson"},
    )

    response = client.get(f"/lessons/?curriculum_id={sample_curriculum}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["curriculum_id"] == sample_curriculum


def test_get_lesson_by_id(sample_curriculum):
    """Test retrieving a specific lesson."""
    # Create lesson
    create_response = client.post(
        "/lessons/", json={"curriculum_id": sample_curriculum, "title": "Test Lesson"}
    )
    lesson_id = create_response.json()["id"]

    response = client.get(f"/lessons/{lesson_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == lesson_id
    assert data["title"] == "Test Lesson"


def test_get_lesson_by_id_not_found():
    """Test retrieving non-existent lesson."""
    response = client.get("/lessons/99999")

    assert response.status_code == 404


def test_update_lesson(sample_curriculum):
    """Test updating a lesson."""
    # Create lesson
    create_response = client.post(
        "/lessons/",
        json={"curriculum_id": sample_curriculum, "title": "Original Title"},
    )
    lesson_id = create_response.json()["id"]

    # Update lesson
    update_payload = {
        "title": "Updated Title",
        "description": "Updated description",
        "lesson_plan_url": "https://example.com/plan",
    }
    response = client.put(f"/lessons/{lesson_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated description"
    assert "example.com" in data["lesson_plan_url"]


def test_update_lesson_partial(sample_curriculum):
    """Test partial update of lesson (only some fields)."""
    # Create lesson with all fields
    create_response = client.post(
        "/lessons/",
        json={
            "curriculum_id": sample_curriculum,
            "title": "Full Lesson",
            "description": "Original description",
            "lesson_plan_url": "https://example.com/original",
        },
    )
    lesson_id = create_response.json()["id"]

    # Update only title
    update_payload = {"title": "Updated Title Only"}
    response = client.put(f"/lessons/{lesson_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title Only"
    # Other fields should remain unchanged
    assert data["description"] == "Original description"
    assert "example.com/original" in data["lesson_plan_url"]


def test_update_lesson_not_found():
    """Test updating non-existent lesson."""
    update_payload = {"title": "New Title"}
    response = client.put("/lessons/99999", json=update_payload)

    assert response.status_code == 404


def test_delete_lesson(sample_curriculum):
    """Test deleting a lesson."""
    # Create lesson
    create_response = client.post(
        "/lessons/", json={"curriculum_id": sample_curriculum, "title": "To Delete"}
    )
    lesson_id = create_response.json()["id"]

    # Delete lesson
    response = client.delete(f"/lessons/{lesson_id}")

    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify deletion
    get_response = client.get(f"/lessons/{lesson_id}")
    assert get_response.status_code == 404


def test_delete_lesson_not_found():
    """Test deleting non-existent lesson."""
    response = client.delete("/lessons/99999")

    assert response.status_code == 404


def test_multiple_lessons_same_curriculum(sample_curriculum):
    """Test that multiple lessons can exist in same curriculum."""
    # Create multiple lessons
    for i in range(5):
        response = client.post(
            "/lessons/",
            json={
                "curriculum_id": sample_curriculum,
                "title": f"Lesson {i + 1}",
            },
        )
        assert response.status_code == 200

    # Verify all exist
    response = client.get(f"/lessons/?curriculum_id={sample_curriculum}")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_lesson_url_formats(sample_curriculum):
    """Test various valid URL formats are accepted."""
    valid_urls = [
        "https://docs.google.com/document/d/abc123",
        "https://drive.google.com/drive/folders/xyz",
        "https://www.dropbox.com/s/abc/file.pdf",
        "http://example.com/lesson",
    ]

    for url in valid_urls:
        response = client.post(
            "/lessons/",
            json={
                "curriculum_id": sample_curriculum,
                "title": f"Lesson with {url}",
                "lesson_plan_url": url,
            },
        )
        assert response.status_code == 200, f"Failed for URL: {url}"


def test_empty_lessons_list():
    """Test getting lessons when none exist."""
    response = client.get("/lessons/")

    assert response.status_code == 200
    data = response.json()
    assert data == []
