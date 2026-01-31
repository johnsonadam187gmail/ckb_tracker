"""Integration tests for curriculum and lesson workflow."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app import models

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"
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


def test_full_curriculum_workflow(sample_class):
    """Test complete workflow: create curriculum -> add lessons -> assign to class instance."""

    # Step 1: Create curriculum
    curriculum_payload = {
        "class_id": sample_class,
        "name": "Full Curriculum",
        "description": "Complete curriculum for testing",
    }
    curr_response = client.post("/curricula/", json=curriculum_payload)
    assert curr_response.status_code == 200
    curriculum_id = curr_response.json()["id"]

    # Step 2: Add multiple lessons to curriculum
    lessons = []
    for i in range(3):
        lesson_payload = {
            "curriculum_id": curriculum_id,
            "title": f"Lesson {i + 1}: Technique {i + 1}",
            "description": f"Description for lesson {i + 1}",
            "lesson_plan_url": f"https://example.com/lesson{i + 1}",
        }
        lesson_response = client.post("/lessons/", json=lesson_payload)
        assert lesson_response.status_code == 200
        lessons.append(lesson_response.json())

    # Verify lessons were created
    assert len(lessons) == 3

    # Step 3: Get all lessons for curriculum
    get_lessons_response = client.get(f"/lessons/?curriculum_id={curriculum_id}")
    assert get_lessons_response.status_code == 200
    fetched_lessons = get_lessons_response.json()
    assert len(fetched_lessons) == 3

    # Step 4: Update a lesson
    lesson_id = lessons[0]["id"]
    update_payload = {
        "title": "Updated Lesson 1",
        "video_folder_url": "https://drive.google.com/updated",
    }
    update_response = client.put(f"/lessons/{lesson_id}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Lesson 1"

    # Step 5: Delete a lesson
    delete_response = client.delete(f"/lessons/{lessons[1]['id']}")
    assert delete_response.status_code == 200

    # Verify lesson count decreased
    get_lessons_after_delete = client.get(f"/lessons/?curriculum_id={curriculum_id}")
    assert len(get_lessons_after_delete.json()) == 2


def test_curriculum_with_class_instance_assignment(sample_class):
    """Test assigning lessons to class instances."""
    from datetime import date

    # Create curriculum and lesson
    curr_response = client.post(
        "/curricula/",
        json={"class_id": sample_class, "name": "Instance Test Curriculum"},
    )
    curriculum_id = curr_response.json()["id"]

    lesson_response = client.post(
        "/lessons/",
        json={
            "curriculum_id": curriculum_id,
            "title": "Guard Passing",
            "lesson_plan_url": "https://example.com/guard-passing",
        },
    )
    lesson_id = lesson_response.json()["id"]

    # Create class instance with lesson
    instance_payload = {
        "class_id": sample_class,
        "class_date": str(date.today()),
        "lesson_id": lesson_id,
        "teacher_uuid": None,
    }

    instance_response = client.post("/class-instances/", json=instance_payload)
    assert instance_response.status_code == 200

    # Verify class instance has lesson reference
    instance_data = instance_response.json()
    assert instance_data["lesson_id"] == lesson_id


def test_delete_curriculum_cascade(sample_class):
    """Test that deleting curriculum with lessons handles cascade properly."""

    # Create curriculum with lessons
    curr_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "To Delete"}
    )
    curriculum_id = curr_response.json()["id"]

    # Add lessons
    for i in range(3):
        client.post(
            "/lessons/",
            json={"curriculum_id": curriculum_id, "title": f"Lesson {i + 1}"},
        )

    # Verify lessons exist
    lessons_before = client.get(f"/lessons/?curriculum_id={curriculum_id}")
    assert len(lessons_before.json()) == 3

    # Delete curriculum
    delete_response = client.delete(f"/curricula/{curriculum_id}")

    # Depending on cascade settings, this test documents expected behavior
    # If cascade delete is enabled, lessons should be deleted too
    if delete_response.status_code == 200:
        # Verify lessons are also gone
        lessons_after = client.get(f"/lessons/?curriculum_id={curriculum_id}")
        assert len(lessons_after.json()) == 0
    else:
        # If cascade not enabled, delete should fail with foreign key constraint
        assert delete_response.status_code == 400


def test_multiple_curricula_different_classes():
    """Test creating curricula for multiple classes."""
    db = TestingSessionLocal()

    # Create multiple classes
    class_ids = []
    for i in range(3):
        class_schedule = models.ClassSchedule(
            class_uuid=f"test-class-uuid-{i}",
            class_name=f"Class {i + 1}",
            day="Monday",
            time=f"{18 + i}:00",
            gym_id=1,
            class_type_id=1,
            is_current=True,
        )
        db.add(class_schedule)
        db.commit()
        db.refresh(class_schedule)
        class_ids.append(class_schedule.id)
    db.close()

    # Create curriculum for each class
    curricula = []
    for i, class_id in enumerate(class_ids):
        response = client.post(
            "/curricula/", json={"class_id": class_id, "name": f"Curriculum {i + 1}"}
        )
        assert response.status_code == 200
        curricula.append(response.json())

    # Verify all curricula exist
    all_curricula = client.get("/curricula/")
    assert len(all_curricula.json()) == 3


def test_lesson_uniqueness_within_curriculum(sample_class):
    """Test that lessons with same title can exist in same curriculum."""

    # Create curriculum
    curr_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "Test"}
    )
    curriculum_id = curr_response.json()["id"]

    # Create multiple lessons with same title (should be allowed)
    for i in range(2):
        response = client.post(
            "/lessons/",
            json={
                "curriculum_id": curriculum_id,
                "title": "Same Title",
                "description": f"Different description {i}",
            },
        )
        assert response.status_code == 200

    # Verify both exist
    lessons = client.get(f"/lessons/?curriculum_id={curriculum_id}")
    assert len(lessons.json()) == 2


def test_curriculum_update_preserves_lessons(sample_class):
    """Test that updating curriculum doesn't affect its lessons."""

    # Create curriculum with lessons
    curr_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "Original"}
    )
    curriculum_id = curr_response.json()["id"]

    lesson_response = client.post(
        "/lessons/", json={"curriculum_id": curriculum_id, "title": "Test Lesson"}
    )
    lesson_id = lesson_response.json()["id"]

    # Update curriculum
    update_response = client.put(
        f"/curricula/{curriculum_id}",
        json={"name": "Updated", "description": "New description"},
    )
    assert update_response.status_code == 200

    # Verify lesson still exists and unchanged
    lesson_check = client.get(f"/lessons/{lesson_id}")
    assert lesson_check.status_code == 200
    assert lesson_check.json()["title"] == "Test Lesson"


def test_get_curriculum_with_lesson_count(sample_class):
    """Test workflow to get curriculum and count its lessons."""

    # Create curriculum
    curr_response = client.post(
        "/curricula/", json={"class_id": sample_class, "name": "Test"}
    )
    curriculum_id = curr_response.json()["id"]

    # Add 5 lessons
    for i in range(5):
        client.post(
            "/lessons/",
            json={"curriculum_id": curriculum_id, "title": f"Lesson {i + 1}"},
        )

    # Get curriculum
    curr = client.get(f"/curricula/{curriculum_id}")
    assert curr.status_code == 200

    # Get lesson count
    lessons = client.get(f"/lessons/?curriculum_id={curriculum_id}")
    assert len(lessons.json()) == 5


def test_error_handling_invalid_references():
    """Test error handling for invalid foreign key references."""

    # Try to create lesson for non-existent curriculum
    lesson_response = client.post(
        "/lessons/", json={"curriculum_id": 99999, "title": "Invalid"}
    )
    assert lesson_response.status_code == 404

    # Try to create curriculum for non-existent class
    curr_response = client.post(
        "/curricula/", json={"class_id": 99999, "name": "Invalid"}
    )
    assert curr_response.status_code == 404
