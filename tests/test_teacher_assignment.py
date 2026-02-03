"""
Unit tests for teacher assignment functionality.
Run with: pytest tests/test_teacher_assignment.py -v
"""

import pytest
from datetime import date, datetime, timezone
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


# Helper functions
def create_user(db, first_name="Test", last_name="User", email=None):
    """Create a test user"""
    if email is None:
        email = f"{first_name.lower()}.{last_name.lower()}@test.com"

    user = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name=first_name,
        last_name=last_name,
        email=email,
        rank="White",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    return user


def assign_role(db, user_uuid, role_name):
    """Assign a role to a user"""
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    user_role = models.UserRole(
        user_uuid=user_uuid,
        role_id=role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    db.add(user_role)
    db.commit()
    return user_role


def create_class(db, class_name="Test Class"):
    """Create a test class"""
    # Create gym and class type first
    gym = models.GymLocation(name="Test Gym", address="123 Test St")
    db.add(gym)
    db.commit()

    class_type = models.ClassType(name="Gi")
    db.add(class_type)
    db.commit()

    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name=class_name,
        day="Monday",
        time="18:00",
        points=1.0,
        gym_id=gym.id,
        class_type_id=class_type.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    db.add(class_schedule)
    db.commit()
    return class_schedule


def create_attendance(db, user_uuid, class_id, teacher_uuid=None, attendance_date=None):
    """Create an attendance record"""
    if attendance_date is None:
        attendance_date = date.today()

    # Get user's Student role for user_role_id
    user_role = (
        db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == user_uuid,
            models.UserRole.is_current == True,
            models.Role.name == "Student",
        )
        .first()
    )

    attendance = models.FactAttendance(
        user_uuid=user_uuid,
        class_id=class_id,
        attendance_date=attendance_date,
        teacher_uuid=teacher_uuid,
        user_role_id=user_role.id if user_role else None,
    )
    db.add(attendance)
    db.commit()
    return attendance


# ============================================================================
# PRIORITY 1: Core Functionality Tests
# ============================================================================


def test_create_attendance_with_teacher(test_db):
    """Test creating attendance record with teacher assigned"""
    # Create users
    student = create_user(test_db, "Student", "One")
    teacher = create_user(test_db, "Teacher", "One")

    # Assign roles
    assign_role(test_db, student.user_uuid, "Student")
    assign_role(test_db, teacher.user_uuid, "Teacher")

    # Create class
    test_class = create_class(test_db)

    # Create attendance with teacher
    attendance = create_attendance(
        test_db, student.user_uuid, test_class.id, teacher_uuid=teacher.user_uuid
    )

    # Verify
    assert attendance.teacher_uuid == teacher.user_uuid
    assert attendance.user_uuid == student.user_uuid

    # Verify teacher relationship works
    saved_attendance = (
        test_db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance.id)
        .first()
    )
    assert saved_attendance.teacher is not None
    assert saved_attendance.teacher.first_name == "Teacher"


def test_create_attendance_without_teacher(test_db):
    """Test creating attendance record with NULL teacher (allowed)"""
    # Create user
    student = create_user(test_db, "Student", "Two")
    assign_role(test_db, student.user_uuid, "Student")

    # Create class
    test_class = create_class(test_db)

    # Create attendance without teacher
    attendance = create_attendance(
        test_db, student.user_uuid, test_class.id, teacher_uuid=None
    )

    # Verify
    assert attendance.teacher_uuid is None
    assert attendance.user_uuid == student.user_uuid

    # Verify teacher relationship returns None (not error)
    saved_attendance = (
        test_db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance.id)
        .first()
    )
    assert saved_attendance.teacher is None


def test_update_teacher_on_attendance(test_db):
    """Test updating teacher on existing attendance record"""
    # Create users
    student = create_user(test_db, "Student", "Three")
    teacher1 = create_user(test_db, "Teacher", "Alpha")
    teacher2 = create_user(test_db, "Teacher", "Beta")

    # Assign roles
    assign_role(test_db, student.user_uuid, "Student")
    assign_role(test_db, teacher1.user_uuid, "Teacher")
    assign_role(test_db, teacher2.user_uuid, "Teacher")

    # Create class and attendance with teacher1
    test_class = create_class(test_db)
    attendance = create_attendance(
        test_db, student.user_uuid, test_class.id, teacher_uuid=teacher1.user_uuid
    )

    # Verify initial teacher
    assert attendance.teacher_uuid == teacher1.user_uuid

    # Update to teacher2
    attendance.teacher_uuid = teacher2.user_uuid
    test_db.commit()

    # Verify update
    updated_attendance = (
        test_db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance.id)
        .first()
    )
    assert updated_attendance.teacher_uuid == teacher2.user_uuid
    assert updated_attendance.teacher.first_name == "Teacher"
    assert updated_attendance.teacher.last_name == "Beta"


def test_teacher_role_validation_logic(test_db):
    """Test that we can check if user has Teacher role"""
    # Create users
    teacher = create_user(test_db, "Real", "Teacher")
    student = create_user(test_db, "Just", "Student")

    # Assign roles
    assign_role(test_db, teacher.user_uuid, "Teacher")
    assign_role(test_db, student.user_uuid, "Student")

    # Check teacher has Teacher role
    teacher_role = (
        test_db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == teacher.user_uuid,
            models.UserRole.is_current == True,
            models.Role.name == "Teacher",
        )
        .first()
    )
    assert teacher_role is not None

    # Check student does NOT have Teacher role
    student_teacher_role = (
        test_db.query(models.UserRole)
        .join(models.Role)
        .filter(
            models.UserRole.user_uuid == student.user_uuid,
            models.UserRole.is_current == True,
            models.Role.name == "Teacher",
        )
        .first()
    )
    assert student_teacher_role is None


def test_get_attendance_by_class_with_teacher(test_db):
    """Test querying attendance by class loads teacher relationship"""
    # Create users
    student1 = create_user(test_db, "Student", "Alpha")
    student2 = create_user(test_db, "Student", "Beta")
    teacher = create_user(test_db, "Teacher", "Main")

    # Assign roles
    assign_role(test_db, student1.user_uuid, "Student")
    assign_role(test_db, student2.user_uuid, "Student")
    assign_role(test_db, teacher.user_uuid, "Teacher")

    # Create class
    test_class = create_class(test_db, "Morning BJJ")

    # Create attendance records
    att1 = create_attendance(
        test_db, student1.user_uuid, test_class.id, teacher.user_uuid
    )
    att2 = create_attendance(
        test_db, student2.user_uuid, test_class.id, teacher.user_uuid
    )

    # Query with eager loading (simulating endpoint)
    from sqlalchemy.orm import joinedload

    records = (
        test_db.query(models.FactAttendance)
        .join(models.ClassSchedule)
        .join(models.User, models.FactAttendance.user_uuid == models.User.user_uuid)
        .filter(models.ClassSchedule.class_name == "Morning BJJ")
        .options(
            joinedload(models.FactAttendance.user),
            joinedload(models.FactAttendance.class_info),
            joinedload(models.FactAttendance.teacher),
        )
        .all()
    )

    # Verify
    assert len(records) == 2
    for r in records:
        assert r.teacher is not None
        assert r.teacher.first_name == "Teacher"
        assert r.teacher.last_name == "Main"


def test_get_attendance_by_class_with_null_teacher(test_db):
    """Test querying attendance with NULL teacher doesn't crash"""
    # Create user
    student = create_user(test_db, "Student", "Solo")
    assign_role(test_db, student.user_uuid, "Student")

    # Create class
    test_class = create_class(test_db, "Self Practice")

    # Create attendance without teacher
    attendance = create_attendance(
        test_db, student.user_uuid, test_class.id, teacher_uuid=None
    )

    # Query with eager loading
    from sqlalchemy.orm import joinedload

    records = (
        test_db.query(models.FactAttendance)
        .join(models.ClassSchedule)
        .join(models.User, models.FactAttendance.user_uuid == models.User.user_uuid)
        .filter(models.ClassSchedule.class_name == "Self Practice")
        .options(
            joinedload(models.FactAttendance.user),
            joinedload(models.FactAttendance.class_info),
            joinedload(models.FactAttendance.teacher),
        )
        .all()
    )

    # Verify - should not crash, teacher should be None
    assert len(records) == 1
    assert records[0].teacher is None
    assert records[0].teacher_uuid is None


# ============================================================================
# PRIORITY 2: Integration Tests
# ============================================================================


def test_full_teacher_assignment_workflow(test_db):
    """Integration test: complete teacher assignment flow"""
    # Step 1: Create users
    student = create_user(test_db, "John", "Doe", "john.doe@test.com")
    teacher = create_user(test_db, "Jane", "Smith", "jane.smith@test.com")

    # Step 2: Assign roles
    student_role = assign_role(test_db, student.user_uuid, "Student")
    teacher_role = assign_role(test_db, teacher.user_uuid, "Teacher")

    assert student_role is not None
    assert teacher_role is not None

    # Step 3: Create class
    test_class = create_class(test_db, "Advanced BJJ")

    # Step 4: Check in student (no teacher initially)
    attendance = create_attendance(test_db, student.user_uuid, test_class.id)
    assert attendance.teacher_uuid is None

    # Step 5: Assign teacher
    attendance.teacher_uuid = teacher.user_uuid
    test_db.commit()

    # Step 6: Verify complete workflow
    final_attendance = (
        test_db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance.id)
        .first()
    )

    assert final_attendance.user_uuid == student.user_uuid
    assert final_attendance.teacher_uuid == teacher.user_uuid
    assert final_attendance.user.first_name == "John"
    assert final_attendance.teacher.first_name == "Jane"


def test_multiple_students_same_teacher(test_db):
    """Test bulk assignment: same teacher to multiple students"""
    # Create teacher
    teacher = create_user(test_db, "Sensei", "Master")
    assign_role(test_db, teacher.user_uuid, "Teacher")

    # Create class
    test_class = create_class(test_db, "Kids Class")

    # Create multiple students and attendance records
    students = []
    attendances = []
    for i in range(5):
        student = create_user(test_db, f"Student", f"Number{i}")
        assign_role(test_db, student.user_uuid, "Student")
        students.append(student)

        attendance = create_attendance(test_db, student.user_uuid, test_class.id)
        attendances.append(attendance)

    # Bulk assign teacher
    for attendance in attendances:
        attendance.teacher_uuid = teacher.user_uuid
    test_db.commit()

    # Verify all have same teacher
    for attendance in attendances:
        saved = (
            test_db.query(models.FactAttendance)
            .filter(models.FactAttendance.id == attendance.id)
            .first()
        )
        assert saved.teacher_uuid == teacher.user_uuid
        assert saved.teacher.first_name == "Sensei"


def test_change_teacher_assignment(test_db):
    """Test changing teacher after initial assignment"""
    # Create users
    student = create_user(test_db, "Student", "Charlie")
    teacher_old = create_user(test_db, "Old", "Teacher")
    teacher_new = create_user(test_db, "New", "Teacher")

    # Assign roles
    assign_role(test_db, student.user_uuid, "Student")
    assign_role(test_db, teacher_old.user_uuid, "Teacher")
    assign_role(test_db, teacher_new.user_uuid, "Teacher")

    # Create class and attendance with old teacher
    test_class = create_class(test_db)
    attendance = create_attendance(
        test_db, student.user_uuid, test_class.id, teacher_uuid=teacher_old.user_uuid
    )

    # Verify old teacher
    assert attendance.teacher_uuid == teacher_old.user_uuid

    # Change to new teacher
    attendance.teacher_uuid = teacher_new.user_uuid
    test_db.commit()

    # Verify change
    updated = (
        test_db.query(models.FactAttendance)
        .filter(models.FactAttendance.id == attendance.id)
        .first()
    )
    assert updated.teacher_uuid == teacher_new.user_uuid
    assert updated.teacher.first_name == "New"


# ============================================================================
# PRIORITY 3: Edge Case Tests
# ============================================================================


def test_empty_class_roster(test_db):
    """Test querying class with no attendance records"""
    # Create class
    test_class = create_class(test_db, "Empty Class")

    # Query attendance (should be empty)
    records = (
        test_db.query(models.FactAttendance)
        .join(models.ClassSchedule)
        .filter(models.ClassSchedule.class_name == "Empty Class")
        .all()
    )

    assert len(records) == 0


def test_date_range_filtering(test_db):
    """Test filtering attendance by date range"""
    # Create user and class
    student = create_user(test_db, "Student", "DateTest")
    assign_role(test_db, student.user_uuid, "Student")
    test_class = create_class(test_db)

    # Create attendance on different dates
    dates = [
        date(2026, 1, 15),
        date(2026, 1, 20),
        date(2026, 1, 25),
    ]

    for d in dates:
        create_attendance(test_db, student.user_uuid, test_class.id, attendance_date=d)

    # Query with date range
    records = (
        test_db.query(models.FactAttendance)
        .filter(
            models.FactAttendance.attendance_date >= date(2026, 1, 18),
            models.FactAttendance.attendance_date <= date(2026, 1, 23),
        )
        .all()
    )

    # Should only get Jan 20
    assert len(records) == 1
    assert records[0].attendance_date == date(2026, 1, 20)


print(
    "✓ All test functions defined. Run with: pytest tests/test_teacher_assignment.py -v"
)
