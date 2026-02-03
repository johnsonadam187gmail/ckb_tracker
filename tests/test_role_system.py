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


# Test 1: Role Model Creation
def test_role_creation(test_db):
    """Test that roles are created correctly"""
    roles = test_db.query(models.Role).all()
    assert len(roles) == 3
    assert {r.name for r in roles} == {"Student", "Teacher", "Admin"}


# Test 2: User Creation with Default Student Role
def test_user_creation_assigns_student_role(test_db):
    """Test that creating a user automatically assigns Student role"""
    # Create user
    user = models.User(
        user_uuid=str(uuid.uuid4()),
        first_name="Test",
        last_name="User",
        email="test@example.com",
        rank="White",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    test_db.add(user)
    test_db.commit()

    # Assign Student role (simulating what the API does)
    student_role = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )
    user_role = models.UserRole(
        user_uuid=user.user_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(user_role)
    test_db.commit()

    # Verify
    user_roles = (
        test_db.query(models.UserRole)
        .filter(
            models.UserRole.user_uuid == user.user_uuid,
            models.UserRole.is_current == True,
        )
        .all()
    )

    assert len(user_roles) == 1
    assert user_roles[0].role.name == "Student"


# Test 3: Multiple Roles Assignment
def test_multiple_roles_assignment(test_db):
    """Test that a user can have multiple roles simultaneously"""
    # Create user
    user_uuid = str(uuid.uuid4())
    user = models.User(
        user_uuid=user_uuid,
        first_name="Multi",
        last_name="Role",
        email="multi@example.com",
        rank="Blue",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    test_db.add(user)
    test_db.commit()

    # Assign multiple roles
    student_role = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )
    teacher_role = (
        test_db.query(models.Role).filter(models.Role.name == "Teacher").first()
    )

    for role in [student_role, teacher_role]:
        user_role = models.UserRole(
            user_uuid=user_uuid,
            role_id=role.id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        test_db.add(user_role)
    test_db.commit()

    # Verify
    user_roles = (
        test_db.query(models.UserRole)
        .filter(
            models.UserRole.user_uuid == user_uuid, models.UserRole.is_current == True
        )
        .all()
    )

    assert len(user_roles) == 2
    role_names = {ur.role.name for ur in user_roles}
    assert role_names == {"Student", "Teacher"}


# Test 4: Role Update with SCD Type 2
def test_role_update_scd_type_2(test_db):
    """Test that role updates create historical records"""
    # Create user with Student role
    user_uuid = str(uuid.uuid4())
    user = models.User(
        user_uuid=user_uuid,
        first_name="SCD",
        last_name="Test",
        email="scd@example.com",
        rank="Purple",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
    )
    test_db.add(user)
    test_db.commit()

    student_role = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )
    user_role = models.UserRole(
        user_uuid=user_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(user_role)
    test_db.commit()

    # Update: Remove Student, Add Teacher
    # 1. Expire old role
    user_role.is_current = False
    user_role.end_date = datetime.now(timezone.utc)

    # 2. Add new role
    teacher_role = (
        test_db.query(models.Role).filter(models.Role.name == "Teacher").first()
    )
    new_user_role = models.UserRole(
        user_uuid=user_uuid,
        role_id=teacher_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(new_user_role)
    test_db.commit()

    # Verify current roles
    current_roles = (
        test_db.query(models.UserRole)
        .filter(
            models.UserRole.user_uuid == user_uuid, models.UserRole.is_current == True
        )
        .all()
    )
    assert len(current_roles) == 1
    assert current_roles[0].role.name == "Teacher"

    # Verify historical record exists
    all_roles = (
        test_db.query(models.UserRole)
        .filter(models.UserRole.user_uuid == user_uuid)
        .all()
    )
    assert len(all_roles) == 2

    expired_role = [r for r in all_roles if not r.is_current][0]
    assert expired_role.role.name == "Student"
    assert expired_role.end_date is not None


# Test 5: Attendance with Teacher Assignment
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

    # Create class
    gym = models.GymLocation(name="Test Gym", address="123 Test St")
    test_db.add(gym)
    test_db.commit()

    class_type = models.ClassType(name="Gi")
    test_db.add(class_type)
    test_db.commit()

    class_schedule = models.ClassSchedule(
        class_uuid=str(uuid.uuid4()),
        class_name="Test Class",
        day="Monday",
        time="18:00",
        points=1.0,
        gym_id=gym.id,
        class_type_id=class_type.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    test_db.add(class_schedule)
    test_db.commit()

    # Assign roles
    student_role = (
        test_db.query(models.Role).filter(models.Role.name == "Student").first()
    )
    teacher_role = (
        test_db.query(models.Role).filter(models.Role.name == "Teacher").first()
    )

    student_ur = models.UserRole(
        user_uuid=student_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )

    teacher_ur = models.UserRole(
        user_uuid=teacher_uuid,
        role_id=teacher_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )

    test_db.add_all([student_ur, teacher_ur])
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
    assert saved_attendance.user.first_name == "Student"


# Test 6: Get Users by Role
def test_get_users_by_role(test_db):
    """Test querying users by role"""
    # Create users with different roles
    users_data = [
        ("Student1", "User", "student1@example.com", "Student"),
        ("Student2", "User", "student2@example.com", "Student"),
        ("Teacher1", "User", "teacher1@example.com", "Teacher"),
        ("Admin1", "User", "admin1@example.com", "Admin"),
    ]

    for first, last, email, role_name in users_data:
        user_uuid = str(uuid.uuid4())
        user = models.User(
            user_uuid=user_uuid,
            first_name=first,
            last_name=last,
            email=email,
            rank="Blue",
            is_current=True,
            created_date=datetime.now(timezone.utc),
            effective_date=datetime.now(timezone.utc),
        )
        test_db.add(user)
        test_db.commit()

        role = test_db.query(models.Role).filter(models.Role.name == role_name).first()
        user_role = models.UserRole(
            user_uuid=user_uuid,
            role_id=role.id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        test_db.add(user_role)
        test_db.commit()

    # Query teachers
    teacher_role = (
        test_db.query(models.Role).filter(models.Role.name == "Teacher").first()
    )
    teacher_uuids = (
        test_db.query(models.UserRole.user_uuid)
        .filter(
            models.UserRole.role_id == teacher_role.id,
            models.UserRole.is_current == True,
        )
        .all()
    )

    teachers = (
        test_db.query(models.User)
        .filter(
            models.User.user_uuid.in_([u[0] for u in teacher_uuids]),
            models.User.is_current == True,
        )
        .all()
    )

    assert len(teachers) == 1
    assert teachers[0].first_name == "Teacher1"


print("All tests defined. Run with: pytest tests/test_role_system.py -v")
