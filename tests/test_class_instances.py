"""
Unit and integration tests for ClassInstance (Lessons) functionality.
Run with: pytest tests/test_class_instances.py -v
"""

import pytest
from datetime import datetime, timezone, date
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


# Test 1: ClassInstance Model Creation
def test_class_instance_creation(test_db):
    """Test that a ClassInstance can be created successfully"""
    # Create a class schedule first
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create a teacher
    teacher = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name="John",
        last_name="Doe",
        email="teacher@example.com",
        rank="Black",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    test_db.add(teacher)
    test_db.commit()

    # Create class instance
    class_instance = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
        teacher_uuid=teacher.user_uuid,
        lesson_title="Introduction to Guard Passing",
        lesson_plan_url="https://docs.google.com/document/123",
        video_folder_url="https://drive.google.com/drive/folders/456",
    )
    test_db.add(class_instance)
    test_db.commit()
    test_db.refresh(class_instance)

    # Verify
    assert class_instance.id is not None
    assert class_instance.class_id == class_schedule.id
    assert class_instance.class_date == date.today()
    assert class_instance.teacher_uuid == teacher.user_uuid
    assert class_instance.lesson_title == "Introduction to Guard Passing"
    assert class_instance.lesson_plan_url == "https://docs.google.com/document/123"
    assert (
        class_instance.video_folder_url == "https://drive.google.com/drive/folders/456"
    )


# Test 2: ClassInstance Unique Constraint
def test_class_instance_unique_constraint(test_db):
    """Test that only one class instance can exist per class_id + class_date"""
    # Create a class schedule
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create first instance
    instance1 = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
        lesson_title="Lesson 1",
    )
    test_db.add(instance1)
    test_db.commit()

    # Try to create duplicate instance
    instance2 = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
        lesson_title="Lesson 2",
    )
    test_db.add(instance2)

    # Should raise IntegrityError
    with pytest.raises(Exception):  # IntegrityError
        test_db.commit()


# Test 3: ClassInstance Relationships
def test_class_instance_relationships(test_db):
    """Test that ClassInstance relationships work correctly"""
    # Create class schedule
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create teacher
    teacher = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name="Jane",
        last_name="Smith",
        email="teacher2@example.com",
        rank="Brown",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    test_db.add(teacher)
    test_db.commit()

    # Create class instance
    class_instance = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
        teacher_uuid=teacher.user_uuid,
    )
    test_db.add(class_instance)
    test_db.commit()
    test_db.refresh(class_instance)

    # Test relationships
    assert class_instance.class_schedule.class_name == "Fundamentals 1"
    assert class_instance.teacher.first_name == "Jane"
    assert class_instance.teacher.last_name == "Smith"


# Test 4: ClassInstance with Null Optional Fields
def test_class_instance_null_fields(test_db):
    """Test that ClassInstance can be created with null optional fields"""
    # Create class schedule
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create class instance with only required fields
    class_instance = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
    )
    test_db.add(class_instance)
    test_db.commit()
    test_db.refresh(class_instance)

    # Verify
    assert class_instance.id is not None
    assert class_instance.teacher_uuid is None
    assert class_instance.lesson_title is None
    assert class_instance.lesson_plan_url is None
    assert class_instance.video_folder_url is None


# Test 5: FactAttendance with ClassInstance Integration
def test_attendance_with_class_instance(test_db):
    """Test that attendance records link to class instances correctly"""
    # Create class schedule
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create student
    student = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name="Student",
        last_name="One",
        email="student@example.com",
        rank="White",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    test_db.add(student)
    test_db.commit()

    # Create class instance
    class_instance = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
        lesson_title="First Lesson",
    )
    test_db.add(class_instance)
    test_db.commit()

    # Create student role
    student_role_def = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )
    student_role = models.UserRole(
        user_uuid=student.user_uuid,
        role_id=student_role_def.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(student_role)
    test_db.commit()

    # Create attendance record
    attendance = models.FactAttendance(
        user_uuid=student.user_uuid,
        class_id=class_schedule.id,
        class_instance_id=class_instance.id,
        attendance_date=date.today(),
        user_role_id=student_role.id,
    )
    test_db.add(attendance)
    test_db.commit()
    test_db.refresh(attendance)

    # Verify relationships
    assert attendance.class_instance_id == class_instance.id
    assert attendance.class_instance.lesson_title == "First Lesson"
    assert len(class_instance.attendance_records) == 1
    assert class_instance.attendance_records[0].user_uuid == student.user_uuid


# Test 6: Multiple Attendance Records to One ClassInstance
def test_multiple_attendance_same_instance(test_db):
    """Test that multiple students can check in to the same class instance"""
    # Create class schedule
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create class instance
    class_instance = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
    )
    test_db.add(class_instance)
    test_db.commit()

    # Create student role
    student_role_def = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )

    # Create multiple students and attendance records
    for i in range(3):
        student = models.User(
            user_uuid=str(uuid.uuid4()),
            first_name=f"Student{i}",
            last_name=f"Test{i}",
            email=f"student{i}@example.com",
            rank="White",
            is_current=True,
            created_date=datetime.now(timezone.utc),
            effective_date=datetime.now(timezone.utc),
        )
        test_db.add(student)
        test_db.flush()

        student_role = models.UserRole(
            user_uuid=student.user_uuid,
            role_id=student_role_def.id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        test_db.add(student_role)
        test_db.flush()

        attendance = models.FactAttendance(
            user_uuid=student.user_uuid,
            class_id=class_schedule.id,
            class_instance_id=class_instance.id,
            attendance_date=date.today(),
            user_role_id=student_role.id,
        )
        test_db.add(attendance)

    test_db.commit()
    test_db.refresh(class_instance)

    # Verify all 3 students are linked to the same class instance
    assert len(class_instance.attendance_records) == 3


# Test 7: ClassInstance Update
def test_class_instance_update(test_db):
    """Test that ClassInstance can be updated"""
    # Create class schedule
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create class instance
    class_instance = models.ClassInstance(
        class_id=class_schedule.id,
        class_date=date.today(),
        lesson_title="Original Title",
    )
    test_db.add(class_instance)
    test_db.commit()

    # Update lesson
    class_instance.lesson_title = "Updated Title"
    class_instance.lesson_plan_url = "https://docs.google.com/updated"
    class_instance.updated_at = datetime.now(timezone.utc)
    test_db.commit()
    test_db.refresh(class_instance)

    # Verify
    assert class_instance.lesson_title == "Updated Title"
    assert class_instance.lesson_plan_url == "https://docs.google.com/updated"


# Test 8: Query ClassInstance by Date Range
def test_query_class_instance_by_date_range(test_db):
    """Test querying class instances by date range"""
    from datetime import timedelta

    # Create class schedule
    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Fundamentals 1",
        day="Monday",
        time="18:00",
        points=1.0,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Create instances for different dates
    today = date.today()
    for i in range(5):
        instance = models.ClassInstance(
            class_id=class_schedule.id,
            class_date=today + timedelta(days=i),
            lesson_title=f"Lesson Day {i}",
        )
        test_db.add(instance)
    test_db.commit()

    # Query instances within range
    start_date = today + timedelta(days=1)
    end_date = today + timedelta(days=3)

    instances = (
        test_db.query(models.ClassInstance)
        .filter(
            models.ClassInstance.class_date >= start_date,
            models.ClassInstance.class_date <= end_date,
        )
        .all()
    )

    # Should return 3 instances (days 1, 2, 3)
    assert len(instances) == 3
    assert all(start_date <= inst.class_date <= end_date for inst in instances)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
