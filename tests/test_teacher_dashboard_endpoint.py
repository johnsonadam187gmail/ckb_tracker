"""
Test the exact endpoint that Teacher Dashboard calls.
This will help identify the 500 error issue.
Run with: pytest tests/test_teacher_dashboard_endpoint.py -v -s
"""

import pytest
from datetime import date, datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app import models
from app.database import Base
from app.routers.attendance import get_class_attendance_detail


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database"""
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


def test_get_class_attendance_endpoint_with_data(test_db):
    """Test the exact endpoint call with real data scenario"""
    print("\n" + "=" * 60)
    print("Testing: GET /attendance/class/{class_name}")
    print("=" * 60)

    # Create gym and class type
    gym = models.GymLocation(name="Test Gym", address="123 Test St")
    test_db.add(gym)
    test_db.commit()

    class_type = models.ClassType(name="Gi")
    test_db.add(class_type)
    test_db.commit()

    # Create class
    test_class = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Morning BJJ",
        day="Monday",
        time="18:00",
        points=1.0,
        gym_id=gym.id,
        class_type_id=class_type.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(test_class)
    test_db.commit()

    # Create student
    student = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name="Test",
        last_name="Student",
        email="test@test.com",
        rank="White",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    test_db.add(student)
    test_db.commit()

    # Assign Student role
    student_role = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )
    user_role = models.UserRole(
        user_uuid=student.user_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(user_role)
    test_db.commit()

    # Create attendance WITHOUT teacher
    attendance = models.FactAttendance(
        user_uuid=student.user_uuid,
        class_id=test_class.id,
        attendance_date=date.today(),
        teacher_uuid=None,  # No teacher assigned
        user_role_id=user_role.id,
    )
    test_db.add(attendance)
    test_db.commit()

    print(f"\nSetup complete:")
    print(f"  Class: {test_class.class_name}")
    print(f"  Student: {student.first_name} {student.last_name}")
    print(f"  Teacher: None (NULL)")
    print(f"  Date: {date.today()}")

    # Call the endpoint function directly
    print(f"\nCalling get_class_attendance_detail()...")
    try:
        result = get_class_attendance_detail(
            class_name="Morning BJJ",
            start_date=date.today(),
            end_date=date.today(),
            rank_filter=None,
            db=test_db,
        )

        print(f"  Status: SUCCESS")
        print(f"  Records returned: {len(result)}")

        if result:
            print(f"  First record:")
            for key, value in result[0].items():
                print(f"    {key}: {value}")

        # Assertions
        assert len(result) == 1
        assert result[0]["userfullname"] == "Test Student"
        assert result[0]["teacher_name"] is None  # Should be None, not crash
        assert result[0]["teacher_uuid"] is None

        print("\n[SUCCESS] Endpoint works correctly with NULL teacher!")

    except Exception as e:
        print(f"  Status: FAILED")
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_get_class_attendance_endpoint_with_teacher(test_db):
    """Test endpoint with teacher assigned"""
    print("\n" + "=" * 60)
    print("Testing: GET /attendance/class/{class_name} WITH teacher")
    print("=" * 60)

    # Create gym and class type
    gym = models.GymLocation(name="Test Gym 2", address="456 Test Ave")
    test_db.add(gym)
    test_db.commit()

    class_type = models.ClassType(name="No-Gi")
    test_db.add(class_type)
    test_db.commit()

    # Create class
    test_class = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Evening BJJ",
        day="Tuesday",
        time="19:00",
        points=1.5,
        gym_id=gym.id,
        class_type_id=class_type.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(test_class)
    test_db.commit()

    # Create student and teacher
    student = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name="Student",
        last_name="Two",
        email="student2@test.com",
        rank="Blue",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )

    teacher = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name="Professor",
        last_name="Smith",
        email="prof@test.com",
        rank="Black",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )

    test_db.add_all([student, teacher])
    test_db.commit()

    # Assign roles
    student_role = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )
    teacher_role = (
        test_db.query(models.Role).filter(models.Role.name == "Teacher").first()
    )

    student_ur = models.UserRole(
        user_uuid=student.user_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )

    teacher_ur = models.UserRole(
        user_uuid=teacher.user_uuid,
        role_id=teacher_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )

    test_db.add_all([student_ur, teacher_ur])
    test_db.commit()

    # Create attendance WITH teacher
    attendance = models.FactAttendance(
        user_uuid=student.user_uuid,
        class_id=test_class.id,
        attendance_date=date.today(),
        teacher_uuid=teacher.user_uuid,  # Teacher assigned
        user_role_id=student_ur.id,
    )
    test_db.add(attendance)
    test_db.commit()

    print(f"\nSetup complete:")
    print(f"  Class: {test_class.class_name}")
    print(f"  Student: {student.first_name} {student.last_name}")
    print(f"  Teacher: {teacher.first_name} {teacher.last_name}")
    print(f"  Date: {date.today()}")

    # Call the endpoint function directly
    print(f"\nCalling get_class_attendance_detail()...")
    try:
        result = get_class_attendance_detail(
            class_name="Evening BJJ",
            start_date=date.today(),
            end_date=date.today(),
            rank_filter=None,
            db=test_db,
        )

        print(f"  Status: SUCCESS")
        print(f"  Records returned: {len(result)}")

        if result:
            print(f"  First record:")
            for key, value in result[0].items():
                print(f"    {key}: {value}")

        # Assertions
        assert len(result) == 1
        assert result[0]["userfullname"] == "Student Two"
        assert result[0]["teacher_name"] == "Professor Smith"
        assert result[0]["teacher_uuid"] == teacher.user_uuid

        print("\n[SUCCESS] Endpoint works correctly with teacher assigned!")

    except Exception as e:
        print(f"  Status: FAILED")
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("Run with: pytest tests/test_teacher_dashboard_endpoint.py -v -s")
