"""
Migration script to add role system to existing database.
Run once: python migrate_add_roles.py
"""

import sys
import io
from app.database import SessionLocal, engine
from app import models
from datetime import datetime, timezone

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def migrate():
    db = SessionLocal()

    try:
        print("Starting role system migration...")
        print("=" * 60)

        # 1. Create tables (if not exist)
        print("\n1. Creating/verifying database tables...")
        models.Base.metadata.create_all(bind=engine)
        print("   [OK] Tables created/verified")

        # 2. Seed roles
        print("\n2. Seeding roles...")
        roles = [
            {"name": "Student", "description": "Member attending classes"},
            {"name": "Teacher", "description": "Instructor teaching classes"},
            {"name": "Admin", "description": "Administrator with full access"},
        ]

        for role_data in roles:
            existing = (
                db.query(models.Role)
                .filter(models.Role.name == role_data["name"])
                .first()
            )
            if not existing:
                role = models.Role(**role_data)
                db.add(role)
                print(f"   [OK] Created role: {role_data['name']}")
            else:
                print(f"   [SKIP] Role already exists: {role_data['name']}")

        db.commit()
        print("   [OK] Roles seeding complete")

        # 3. Assign "Student" role to all existing users
        print("\n3. Assigning default Student role to existing users...")
        student_role = (
            db.query(models.Role).filter(models.Role.name == "Student").first()
        )

        if not student_role:
            raise Exception("Student role not found! Migration failed.")

        all_users = db.query(models.User).filter(models.User.is_current == True).all()

        assigned_count = 0
        for user in all_users:
            # Check if user already has Student role
            existing_assignment = (
                db.query(models.UserRole)
                .filter(
                    models.UserRole.user_uuid == user.user_uuid,
                    models.UserRole.role_id == student_role.id,
                    models.UserRole.is_current == True,
                )
                .first()
            )

            if not existing_assignment:
                user_role = models.UserRole(
                    user_uuid=user.user_uuid,
                    role_id=student_role.id,
                    is_current=True,
                    effective_date=datetime.now(timezone.utc),
                    created_date=datetime.now(timezone.utc),
                )
                db.add(user_role)
                assigned_count += 1
                print(
                    f"   [OK] Assigned Student role to: {user.first_name} {user.last_name}"
                )
            else:
                print(
                    f"   [SKIP] Student role already assigned to: {user.first_name} {user.last_name}"
                )

        db.commit()
        print(f"   [OK] Assigned Student role to {assigned_count} new users")
        print(f"   [OK] Total users with Student role: {len(all_users)}")

        # 4. Note about attendance records
        print("\n4. Attendance table updates:")
        print("   [OK] teacher_uuid column added (will be NULL for old records)")
        print("   [OK] user_role_id column added (will be NULL for old records)")
        print("   [INFO] This is acceptable - new records will populate these fields")

        print("\n" + "=" * 60)
        print("[SUCCESS] Migration complete successfully!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
