"""
Test for photo upload fix with SCD Type 2 versioning.
This test verifies the database constraint fix for photo updates.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from PIL import Image
import io

from app import models
from app.database import Base
from app.services.cloudinary_service import cloudinary_service


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


def create_test_image():
    """Create a simple test image"""
    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes.read()


def test_user_scd_versioning(test_db):
    """Test that SCD Type 2 versioning works with the composite unique constraint"""
    # Create initial user
    user_uuid = str(uuid.uuid4())
    user_v1 = models.User(
        user_uuid=user_uuid,
        first_name="Test",
        last_name="User",
        email="test@example.com",
        rank="White",
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
        profile_image_url="https://example.com/photo1.jpg",
    )
    test_db.add(user_v1)
    test_db.commit()

    # Verify first version exists
    current = (
        test_db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == True)
        .first()
    )
    assert current is not None
    assert current.profile_image_url == "https://example.com/photo1.jpg"

    # Create new version (simulating photo update)
    now = datetime.now(timezone.utc)
    user_v1.is_current = False
    user_v1.end_date = now
    user_v1.updated_date = now

    user_v2 = models.User(
        user_uuid=user_uuid,
        first_name="Test",
        last_name="User",
        email="test@example.com",
        rank="White",
        is_current=True,
        effective_date=now,
        created_date=user_v1.created_date,
        updated_date=now,
        profile_image_url="https://example.com/photo2.jpg",
    )
    test_db.add(user_v2)
    test_db.commit()

    # Verify versioning worked
    all_versions = (
        test_db.query(models.User).filter(models.User.user_uuid == user_uuid).all()
    )
    assert len(all_versions) == 2

    current = (
        test_db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == True)
        .first()
    )
    assert current.profile_image_url == "https://example.com/photo2.jpg"

    old = (
        test_db.query(models.User)
        .filter(models.User.user_uuid == user_uuid, models.User.is_current == False)
        .first()
    )
    assert old.profile_image_url == "https://example.com/photo1.jpg"


def test_unique_constraint_enforced(test_db):
    """Test that the composite unique constraint prevents duplicate current versions"""
    user_uuid = str(uuid.uuid4())

    # Create first current version
    user1 = models.User(
        user_uuid=user_uuid,
        first_name="Test",
        last_name="User",
        email="test@example.com",
        rank="White",
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(user1)
    test_db.commit()

    # Try to create another current version with same UUID - should fail
    user2 = models.User(
        user_uuid=user_uuid,
        first_name="Test",
        last_name="User",
        email="test2@example.com",  # Different email
        rank="Blue",  # Different rank
        is_current=True,  # Same is_current = True
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(user2)

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        test_db.commit()

    test_db.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
