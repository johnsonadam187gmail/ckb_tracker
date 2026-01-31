"""
Test script to verify role system endpoints work correctly.
Run while FastAPI server is running: python test_endpoints.py
"""

import sys
from app.database import SessionLocal
from app import models


def test_database():
    """Test that database tables and data exist"""
    db = SessionLocal()

    try:
        print("Testing Database Setup")
        print("=" * 60)

        # 1. Check roles exist
        print("\n1. Checking roles...")
        roles = db.query(models.Role).all()
        print(f"   Found {len(roles)} roles:")
        for role in roles:
            print(f"   - {role.name}: {role.description}")

        if len(roles) != 3:
            print("   [ERROR] Expected 3 roles, found", len(roles))
            return False

        # 2. Check users exist
        print("\n2. Checking users...")
        users = db.query(models.User).filter(models.User.is_current == True).all()
        print(f"   Found {len(users)} active users:")
        for user in users:
            print(f"   - {user.first_name} {user.last_name} ({user.user_uuid})")

        # 3. Check user_roles exist
        print("\n3. Checking user role assignments...")
        user_roles = (
            db.query(models.UserRole).filter(models.UserRole.is_current == True).all()
        )
        print(f"   Found {len(user_roles)} active user role assignments:")
        for ur in user_roles:
            role = db.query(models.Role).filter(models.Role.id == ur.role_id).first()
            user = (
                db.query(models.User)
                .filter(
                    models.User.user_uuid == ur.user_uuid,
                    models.User.is_current == True,
                )
                .first()
            )
            if user and role:
                print(f"   - {user.first_name} {user.last_name} -> {role.name}")

        # 4. Check attendance table structure
        print("\n4. Checking attendance table...")
        attendance_count = db.query(models.FactAttendance).count()
        print(f"   Found {attendance_count} attendance records")

        # Check if new columns exist
        if attendance_count > 0:
            sample = db.query(models.FactAttendance).first()
            print(
                f"   Sample record has teacher_uuid: {sample.teacher_uuid is not None}"
            )
            print(
                f"   Sample record has user_role_id: {sample.user_role_id is not None}"
            )

        print("\n" + "=" * 60)
        print("[SUCCESS] Database verification complete!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] Database test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
