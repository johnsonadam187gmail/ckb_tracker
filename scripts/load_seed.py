#!/usr/bin/env python3
"""
CKB Tracker Database Seed Loader

This script loads a JSON seed file into the database.
Can be run manually or scheduled via cron.

Usage:
    python scripts/load_seed.py seeds/seed_20260218_143022.json
    python scripts/load_seed.py seeds/seed_20260218_143022.json --clear-only

For cron scheduling (daily at 2 AM):
    0 2 * * * cd /path/to/ckb_tracker && python scripts/load_seed.py seeds/latest.json
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, SessionLocal
from app.models import (
    Base,
    User,
    Role,
    UserRole,
    ClassSchedule,
    GymLocation,
    ClassType,
    Term,
    TermTarget,
    Curriculum,
    Lesson,
    ClassInstance,
    FactAttendance,
    ClassFeedback,
    KioskAuth,
)
from app.auth import get_password_hash


def reset_database():
    """Reset database to empty state with only roles."""
    print("🔄 Resetting database...")

    # Drop all tables
    Base.metadata.drop_all(bind=engine)

    # Recreate all tables
    Base.metadata.create_all(bind=engine)

    # Seed default roles
    db = SessionLocal()
    try:
        roles = [
            Role(name="Student", description="Member attending classes"),
            Role(name="Teacher", description="Instructor teaching classes"),
            Role(name="Admin", description="Administrator with full access"),
        ]
        for role in roles:
            db.add(role)
        db.commit()
        print("✅ Database reset with default roles")
    except Exception as e:
        print(f"❌ Error seeding roles: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def load_seed_data(seed_path: str):
    """Load seed data from JSON file."""
    print(f"📂 Loading seed file: {seed_path}")

    with open(seed_path, "r") as f:
        seed_data = json.load(f)

    metadata = seed_data.get("metadata", {})
    data = seed_data.get("data", {})

    print(f"📊 Seed metadata:")
    print(f"   Exported: {metadata.get('exported_at', 'Unknown')}")
    print(f"   Version: {metadata.get('version', 'Unknown')}")

    record_counts = metadata.get("record_counts", {})
    for table, count in record_counts.items():
        print(f"   {table}: {count} records")

    db = SessionLocal()
    try:
        # Load gym locations first (no dependencies)
        if "gym_locations" in data:
            print("\n🏢 Loading gym locations...")
            for gym_data in data["gym_locations"]:
                gym = GymLocation(
                    id=gym_data.get("id"),
                    name=gym_data["name"],
                    address=gym_data.get("address"),
                )
                db.add(gym)
            db.commit()
            print(f"   ✅ Loaded {len(data['gym_locations'])} gym locations")

        # Load class types
        if "class_types" in data:
            print("\n📋 Loading class types...")
            for type_data in data["class_types"]:
                class_type = ClassType(id=type_data.get("id"), name=type_data["name"])
                db.add(class_type)
            db.commit()
            print(f"   ✅ Loaded {len(data['class_types'])} class types")

        # Load terms
        if "terms" in data:
            print("\n📅 Loading terms...")
            for term_data in data["terms"]:
                from datetime import date

                term = Term(
                    id=term_data.get("id"),
                    term_name=term_data["term_name"],
                    start_date=date.fromisoformat(term_data["start_date"]),
                    end_date=date.fromisoformat(term_data["end_date"]),
                    created_at=datetime.fromisoformat(term_data["created_at"]),
                )
                db.add(term)
            db.commit()
            print(f"   ✅ Loaded {len(data['terms'])} terms")

        # Load term targets
        if "term_targets" in data:
            print("\n🎯 Loading term targets...")
            for target_data in data["term_targets"]:
                target = TermTarget(
                    id=target_data.get("id"),
                    term_id=target_data["term_id"],
                    rank=target_data["rank"],
                    target=target_data["target"],
                )
                db.add(target)
            db.commit()
            print(f"   ✅ Loaded {len(data['term_targets'])} term targets")

        # Load users
        if "users" in data:
            print("\n👥 Loading users...")
            for user_data in data["users"]:
                from datetime import date

                user = User(
                    id=user_data.get("id"),
                    user_uuid=user_data["user_uuid"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    email=user_data["email"],
                    password_hash=user_data.get("password_hash"),
                    rank=user_data.get("rank"),
                    last_graded_date=date.fromisoformat(user_data["last_graded_date"])
                    if user_data.get("last_graded_date")
                    else None,
                    comments=user_data.get("comments"),
                    nicknames=user_data.get("nicknames"),
                    profile_image_url=user_data.get("profile_image_url"),
                    is_current=user_data.get("is_current", True),
                    effective_date=datetime.fromisoformat(user_data["effective_date"]),
                    end_date=datetime.fromisoformat(user_data["end_date"])
                    if user_data.get("end_date")
                    else None,
                    created_date=datetime.fromisoformat(user_data["created_date"]),
                    updated_date=datetime.fromisoformat(user_data["updated_date"]),
                )
                db.add(user)
            db.commit()
            print(f"   ✅ Loaded {len(data['users'])} users")

        # Load user roles
        if "user_roles" in data:
            print("\n👤 Loading user roles...")
            for role_data in data["user_roles"]:
                user_role = UserRole(
                    id=role_data.get("id"),
                    user_uuid=role_data["user_uuid"],
                    role_id=role_data["role_id"],
                    is_current=role_data.get("is_current", True),
                    effective_date=datetime.fromisoformat(role_data["effective_date"]),
                    end_date=datetime.fromisoformat(role_data["end_date"])
                    if role_data.get("end_date")
                    else None,
                    created_date=datetime.fromisoformat(role_data["created_date"]),
                    updated_date=datetime.fromisoformat(role_data["updated_date"]),
                )
                db.add(user_role)
            db.commit()
            print(f"   ✅ Loaded {len(data['user_roles'])} user roles")

        # Load class schedules
        if "classes" in data:
            print("\n📚 Loading class schedules...")
            for class_data in data["classes"]:
                class_schedule = ClassSchedule(
                    id=class_data.get("id"),
                    class_uuid=class_data["class_uuid"],
                    class_name=class_data["class_name"],
                    day=class_data["day"],
                    time=class_data["time"],
                    description=class_data.get("description"),
                    points=class_data.get("points", 1.0),
                    gym_id=class_data["gym_id"],
                    class_type_id=class_data["class_type_id"],
                    is_current=class_data.get("is_current", True),
                    effective_date=datetime.fromisoformat(class_data["effective_date"]),
                    end_date=datetime.fromisoformat(class_data["end_date"])
                    if class_data.get("end_date")
                    else None,
                    created_date=datetime.fromisoformat(class_data["created_date"]),
                )
                db.add(class_schedule)
            db.commit()
            print(f"   ✅ Loaded {len(data['classes'])} class schedules")

        # Load curricula
        if "curricula" in data:
            print("\n📖 Loading curricula...")
            for curr_data in data["curricula"]:
                curriculum = Curriculum(
                    id=curr_data.get("id"),
                    class_id=curr_data["class_id"],
                    name=curr_data["name"],
                    description=curr_data.get("description"),
                    created_at=datetime.fromisoformat(curr_data["created_at"]),
                    updated_at=datetime.fromisoformat(curr_data["updated_at"]),
                )
                db.add(curriculum)
            db.commit()
            print(f"   ✅ Loaded {len(data['curricula'])} curricula")

        # Load lessons
        if "lessons" in data:
            print("\n📝 Loading lessons...")
            for lesson_data in data["lessons"]:
                lesson = Lesson(
                    id=lesson_data.get("id"),
                    curriculum_id=lesson_data["curriculum_id"],
                    title=lesson_data["title"],
                    description=lesson_data.get("description"),
                    lesson_plan_url=lesson_data.get("lesson_plan_url"),
                    video_folder_url=lesson_data.get("video_folder_url"),
                    created_at=datetime.fromisoformat(lesson_data["created_at"]),
                    updated_at=datetime.fromisoformat(lesson_data["updated_at"]),
                )
                db.add(lesson)
            db.commit()
            print(f"   ✅ Loaded {len(data['lessons'])} lessons")

        # Load class instances
        if "class_instances" in data:
            print("\n📆 Loading class instances...")
            from datetime import date

            for instance_data in data["class_instances"]:
                instance = ClassInstance(
                    id=instance_data.get("id"),
                    class_id=instance_data["class_id"],
                    class_date=date.fromisoformat(instance_data["class_date"]),
                    teacher_uuid=instance_data.get("teacher_uuid"),
                    lesson_id=instance_data.get("lesson_id"),
                    created_at=datetime.fromisoformat(instance_data["created_at"]),
                    updated_at=datetime.fromisoformat(instance_data["updated_at"]),
                )
                db.add(instance)
            db.commit()
            print(f"   ✅ Loaded {len(data['class_instances'])} class instances")

        # Load attendance records
        if "attendance" in data:
            print("\n✓ Loading attendance records...")
            from datetime import date

            for att_data in data["attendance"]:
                attendance = FactAttendance(
                    id=att_data.get("id"),
                    user_uuid=att_data["user_uuid"],
                    class_id=att_data["class_id"],
                    class_instance_id=att_data.get("class_instance_id"),
                    teacher_uuid=att_data.get("teacher_uuid"),
                    user_role_id=att_data.get("user_role_id"),
                    attendance_date=date.fromisoformat(att_data["attendance_date"]),
                    created_at=datetime.fromisoformat(att_data["created_at"]),
                    status=att_data.get("status", "confirmed"),
                    confirmed_by=att_data.get("confirmed_by"),
                    confirmed_at=datetime.fromisoformat(att_data["confirmed_at"])
                    if att_data.get("confirmed_at")
                    else None,
                )
                db.add(attendance)
            db.commit()
            print(f"   ✅ Loaded {len(data['attendance'])} attendance records")

        # Load feedback
        if "class_feedback" in data:
            print("\n💬 Loading class feedback...")
            for feedback_data in data["class_feedback"]:
                feedback = ClassFeedback(
                    id=feedback_data.get("id"),
                    user_uuid=feedback_data["user_uuid"],
                    attendance_id=feedback_data["attendance_id"],
                    class_instance_id=feedback_data["class_instance_id"],
                    rating=feedback_data.get("rating"),
                    comment=feedback_data.get("comment"),
                    created_at=datetime.fromisoformat(feedback_data["created_at"]),
                    updated_at=datetime.fromisoformat(feedback_data["updated_at"]),
                )
                db.add(feedback)
            db.commit()
            print(f"   ✅ Loaded {len(data['class_feedback'])} feedback entries")

        # Load kiosk auth (if present)
        if "kiosk_auth" in data and data["kiosk_auth"]:
            print("\n🔐 Loading kiosk auth...")
            for kiosk_data in data["kiosk_auth"]:
                kiosk = KioskAuth(
                    id=kiosk_data.get("id"),
                    pin_hash=kiosk_data["pin_hash"],
                    created_at=datetime.fromisoformat(kiosk_data["created_at"]),
                    updated_at=datetime.fromisoformat(kiosk_data["updated_at"]),
                )
                db.add(kiosk)
            db.commit()
            print(f"   ✅ Loaded {len(data['kiosk_auth'])} kiosk auth records")

        print("\n" + "=" * 60)
        print("✅ Seed data loaded successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error loading seed data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Load seed data into CKB Tracker database"
    )
    parser.add_argument("seed_file", help="Path to the JSON seed file")
    parser.add_argument(
        "--clear-only",
        action="store_true",
        help="Only reset database without loading seed data",
    )

    args = parser.parse_args()

    seed_path = Path(args.seed_file)

    if not seed_path.exists():
        print(f"❌ Seed file not found: {seed_path}")
        sys.exit(1)

    # Reset database first
    reset_database()

    # Load seed data if not clear-only mode
    if not args.clear_only:
        load_seed_data(str(seed_path))
    else:
        print("\n✅ Database reset complete (seed loading skipped)")


if __name__ == "__main__":
    main()
