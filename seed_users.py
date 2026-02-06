"""
Seed script to create initial users with passwords for testing.

Creates:
- 1 Admin user (can access Settings page)
- 1 Teacher user (can teach classes and access Teacher Dashboard)
- 1 Student user (can check in to classes)

DEFAULT PASSWORDS (CHANGE THESE IN PRODUCTION!):
- Admin: admin123
- Teacher: teacher123
- Student: student123
"""

from app.database import SessionLocal
from app.models import User, Role, UserRole
from app.auth import get_password_hash
from datetime import datetime, timezone
import uuid

db = SessionLocal()

try:
    # Fetch roles
    student_role = db.query(Role).filter(Role.name == "Student").first()
    teacher_role = db.query(Role).filter(Role.name == "Teacher").first()
    admin_role = db.query(Role).filter(Role.name == "Admin").first()

    if not all([student_role, teacher_role, admin_role]):
        print("[ERROR] Roles not found. Run reset_db.py first!")
        exit(1)

    # 1. Create Admin User
    admin_uuid = str(uuid.uuid4())
    admin_user = User(
        user_uuid=admin_uuid,
        first_name="Admin",
        last_name="User",
        email="admin@ckb.com",
        password_hash=get_password_hash("admin123"),
        rank="Black",
        comments="System administrator",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
        updated_date=datetime.now(timezone.utc),
    )
    db.add(admin_user)
    db.commit()

    # Assign Admin role
    admin_user_role = UserRole(
        user_uuid=admin_uuid,
        role_id=admin_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    db.add(admin_user_role)
    db.commit()

    print("✅ Created Admin User:")
    print(f"   Email: admin@ckb.com")
    print(f"   Password: admin123")
    print(f"   UUID: {admin_uuid}")

    # 2. Create Teacher User
    teacher_uuid = str(uuid.uuid4())
    teacher_user = User(
        user_uuid=teacher_uuid,
        first_name="John",
        last_name="Instructor",
        email="teacher@ckb.com",
        password_hash=get_password_hash("teacher123"),
        rank="Brown",
        comments="BJJ instructor",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
        updated_date=datetime.now(timezone.utc),
    )
    db.add(teacher_user)
    db.commit()

    # Assign Teacher and Student roles
    teacher_user_role_teacher = UserRole(
        user_uuid=teacher_uuid,
        role_id=teacher_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    teacher_user_role_student = UserRole(
        user_uuid=teacher_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    db.add(teacher_user_role_teacher)
    db.add(teacher_user_role_student)
    db.commit()

    print("✅ Created Teacher User:")
    print(f"   Email: teacher@ckb.com")
    print(f"   Password: teacher123")
    print(f"   UUID: {teacher_uuid}")

    # 3. Create Student User
    student_uuid = str(uuid.uuid4())
    student_user = User(
        user_uuid=student_uuid,
        first_name="Mike",
        last_name="Student",
        email="student@ckb.com",
        password_hash=get_password_hash("student123"),
        rank="Blue",
        comments="Regular student",
        is_current=True,
        created_date=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
        updated_date=datetime.now(timezone.utc),
    )
    db.add(student_user)
    db.commit()

    # Assign Student role
    student_user_role = UserRole(
        user_uuid=student_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    db.add(student_user_role)
    db.commit()

    print("✅ Created Student User:")
    print(f"   Email: student@ckb.com")
    print(f"   Password: student123")
    print(f"   UUID: {student_uuid}")

    print("\n" + "=" * 60)
    print("🎉 Seed data created successfully!")
    print("=" * 60)
    print("\n📋 CREDENTIALS SUMMARY:")
    print("\n1. Admin (Settings Page Access):")
    print("   Email: admin@ckb.com")
    print("   Password: admin123")
    print("\n2. Teacher (Teacher Dashboard Access):")
    print("   Email: teacher@ckb.com")
    print("   Password: teacher123")
    print("\n3. Student (Can check in to classes):")
    print("   Email: student@ckb.com")
    print("   Password: student123")
    print("\n⚠️  IMPORTANT: Change these passwords in production!")
    print("=" * 60)

except Exception as e:
    print(f"❌ Error creating seed data: {e}")
    db.rollback()
finally:
    db.close()
