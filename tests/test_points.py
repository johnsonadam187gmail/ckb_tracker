"""
Simple test to validate points field (formerly weighting).
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app import models
from app.database import Base


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_class_points_field(test_db):
    """Test that the points field (formerly weighting) works correctly."""
    # Create a class with points
    class_uuid = str(uuid.uuid4())
    points_value = 1.5

    class_schedule = models.ClassSchedule(
        class_uuid=class_uuid,
        class_name="Test Class",
        day="Monday",
        time="18:00",
        points=points_value,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()
    test_db.refresh(class_schedule)

    # Retrieve the class and verify points
    retrieved_class = (
        test_db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.class_uuid == class_uuid)
        .first()
    )

    # Assertions
    assert retrieved_class is not None
    assert hasattr(retrieved_class, "points")
    assert retrieved_class.points == points_value

    # Verify we can modify the points
    new_points = 2.0
    retrieved_class.points = new_points
    test_db.commit()
    test_db.refresh(retrieved_class)

    assert retrieved_class.points == new_points
