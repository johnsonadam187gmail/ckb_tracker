"""
Complete seed data script for CKB Tracker.

Creates:
- 3 users (admin, teacher, student) with passwords
- 2 gym locations
- 3 class types
- 6 classes (scheduled classes)
- 1 term with targets
- Multiple attendance records (check-ins)
- Multiple feedback entries (both positive and negative)
- 1 curriculum with 3 lessons
- Class instances with teacher assignments

Run this after reset_db.py to get a fully populated test database.
"""

from app.database import SessionLocal
from app.models import (
    User,
    Role,
    UserRole,
    ClassSchedule,
    GymLocation,
    ClassType,
    Term,
    TermTarget,
    FactAttendance,
    ClassFeedback,
    ClassInstance,
    Curriculum,
    Lesson,
)
from app.auth import get_password_hash
from datetime import datetime, timezone, date, timedelta
import uuid

db = SessionLocal()

try:
    print("=" * 60)
    print("🌱 SEEDING COMPLETE TEST DATA")
    print("=" * 60)

    # Fetch roles
    student_role = db.query(Role).filter(Role.name == "Student").first()
    teacher_role = db.query(Role).filter(Role.name == "Teacher").first()
    admin_role = db.query(Role).filter(Role.name == "Admin").first()

    if not all([student_role, teacher_role, admin_role]):
        print("❌ Error: Roles not found. Run reset_db.py first!")
        exit(1)

    # ===== 1. CREATE USERS =====
    print("\n📋 Creating Users...")

    # Admin User
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

    admin_user_role = UserRole(
        user_uuid=admin_uuid,
        role_id=admin_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    db.add(admin_user_role)
    db.commit()
    print(f"   ✅ Admin: admin@ckb.com / admin123")

    # Teacher User
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
    print(f"   ✅ Teacher: teacher@ckb.com / teacher123")

    # Student User
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

    student_user_role = UserRole(
        user_uuid=student_uuid,
        role_id=student_role.id,
        is_current=True,
        effective_date=datetime.now(timezone.utc),
        created_date=datetime.now(timezone.utc),
    )
    db.add(student_user_role)
    db.commit()
    print(f"   ✅ Student: student@ckb.com / student123")

    # Additional Students for realistic data
    additional_students = []
    student_names = [
        ("Sarah", "Martinez", "Purple"),
        ("James", "Anderson", "White"),
        ("Emma", "Wilson", "Blue"),
        ("David", "Thompson", "Purple"),
    ]

    for first, last, rank in student_names:
        student_uuid_new = str(uuid.uuid4())
        new_student = User(
            user_uuid=student_uuid_new,
            first_name=first,
            last_name=last,
            email=f"{first.lower()}.{last.lower()}@ckb.com",
            password_hash=get_password_hash("student123"),
            rank=rank,
            comments=f"{rank} belt student",
            is_current=True,
            created_date=datetime.now(timezone.utc),
            effective_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc),
        )
        db.add(new_student)
        db.commit()

        new_student_role = UserRole(
            user_uuid=student_uuid_new,
            role_id=student_role.id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        db.add(new_student_role)
        db.commit()
        additional_students.append(student_uuid_new)
        print(
            f"   ✅ {first} {last}: {first.lower()}.{last.lower()}@ckb.com / student123"
        )

    # ===== 2. CREATE GYM LOCATIONS =====
    print("\n🏢 Creating Gym Locations...")

    gym_main = GymLocation(
        name="CKB Main Gym",
        address="123 Main Street, San Diego, CA",
    )
    db.add(gym_main)

    gym_north = GymLocation(
        name="CKB North Location",
        address="456 North Ave, San Diego, CA",
    )
    db.add(gym_north)
    db.commit()
    print(f"   ✅ Main Gym: {gym_main.name}")
    print(f"   ✅ North Location: {gym_north.name}")

    # ===== 3. CREATE CLASS TYPES =====
    print("\n🥋 Creating Class Types...")

    type_gi = ClassType(
        name="Gi",
    )
    db.add(type_gi)

    type_nogi = ClassType(
        name="No-Gi",
    )
    db.add(type_nogi)

    type_comp = ClassType(
        name="Competition",
    )
    db.add(type_comp)
    db.commit()
    print(f"   ✅ {type_gi.name}")
    print(f"   ✅ {type_nogi.name}")
    print(f"   ✅ {type_comp.name}")

    # ===== 4. CREATE CLASSES =====
    print("\n📅 Creating Class Schedule...")

    classes_data = [
        (
            "Fundamentals 1",
            "Monday",
            "18:00",
            "Beginner fundamentals",
            1.0,
            gym_main.id,
            type_gi.id,
        ),
        (
            "Fundamentals 2",
            "Wednesday",
            "18:00",
            "Intermediate fundamentals",
            1.0,
            gym_main.id,
            type_gi.id,
        ),
        (
            "Advanced Gi",
            "Tuesday",
            "19:30",
            "Advanced techniques with gi",
            1.5,
            gym_main.id,
            type_gi.id,
        ),
        (
            "No-Gi Basics",
            "Thursday",
            "18:00",
            "No-gi fundamentals",
            1.0,
            gym_main.id,
            type_nogi.id,
        ),
        (
            "Competition Class",
            "Saturday",
            "10:00",
            "Competition prep and rolling",
            2.0,
            gym_main.id,
            type_comp.id,
        ),
        (
            "Open Mat",
            "Sunday",
            "11:00",
            "Open mat for all levels",
            1.0,
            gym_north.id,
            type_nogi.id,
        ),
    ]

    created_classes = []
    for name, day, time, desc, points, gym_id, type_id in classes_data:
        class_uuid = str(uuid.uuid4())
        new_class = ClassSchedule(
            class_uuid=class_uuid,
            class_name=name,
            day=day,
            time=time,
            description=desc,
            points=points,
            gym_id=gym_id,
            class_type_id=type_id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        db.add(new_class)
        db.commit()
        created_classes.append(new_class)
        print(f"   ✅ {name} - {day} {time}")

    # ===== 5. CREATE TERM =====
    print("\n🗓️ Creating Term...")

    term_start = date.today() - timedelta(days=30)
    term_end = date.today() + timedelta(days=60)

    term = Term(
        term_name="Spring 2026",
        start_date=term_start,
        end_date=term_end,
        created_at=datetime.now(timezone.utc),
    )
    db.add(term)
    db.commit()
    print(f"   ✅ {term.term_name} ({term_start} to {term_end})")

    # ===== 6. CREATE TERM TARGETS =====
    print("\n🎯 Creating Term Targets...")

    targets_data = [
        ("White", 40.0),
        ("Blue", 60.0),
        ("Purple", 80.0),
        ("Brown", 100.0),
        ("Black", 120.0),
    ]

    for rank, target_val in targets_data:
        target_obj = TermTarget(
            term_id=term.id,
            rank=rank,
            target=target_val,
        )
        db.add(target_obj)
        print(f"   ✅ {rank}: {target_val} points")
    db.commit()

    # ===== 7. CREATE CURRICULUM & LESSONS =====
    print("\n📚 Creating Curriculum & Lessons...")

    # Create curriculum for Fundamentals 1
    fundamentals_class = created_classes[0]  # Fundamentals 1
    curriculum = Curriculum(
        class_id=fundamentals_class.id,
        name="Fundamentals 1 Curriculum",
        description="Core techniques for beginners",
        created_at=datetime.now(timezone.utc),
    )
    db.add(curriculum)
    db.commit()
    print(f"   ✅ Curriculum: {curriculum.name}")

    # Create lessons
    lessons_data = [
        (
            "Guard Passing Basics",
            "Learn fundamental guard passing techniques",
            "https://example.com/lesson1",
            "https://example.com/videos1",
        ),
        (
            "Side Control Escapes",
            "Escaping side control position",
            "https://example.com/lesson2",
            "https://example.com/videos2",
        ),
        (
            "Mount Control",
            "Maintaining and attacking from mount",
            "https://example.com/lesson3",
            "https://example.com/videos3",
        ),
    ]

    created_lessons = []
    for title, desc, plan_url, video_url in lessons_data:
        lesson = Lesson(
            curriculum_id=curriculum.id,
            title=title,
            description=desc,
            lesson_plan_url=plan_url,
            video_folder_url=video_url,
            created_at=datetime.now(timezone.utc),
        )
        db.add(lesson)
        db.commit()
        created_lessons.append(lesson)
        print(f"   ✅ Lesson: {title}")

    # ===== 8. CREATE ATTENDANCE & CLASS INSTANCES =====
    print("\n✅ Creating Attendance Records & Class Instances...")

    all_student_uuids = [student_uuid] + additional_students

    # Create attendance for past 7 days
    attendance_records = []
    for days_ago in range(7, 0, -1):
        attendance_date = date.today() - timedelta(days=days_ago)

        # Select 2-3 classes per day
        for class_obj in created_classes[:3]:  # Use first 3 classes
            # Create ClassInstance with teacher and lesson
            lesson_to_assign = created_lessons[days_ago % len(created_lessons)]

            class_instance = ClassInstance(
                class_id=class_obj.id,
                class_date=attendance_date,
                teacher_uuid=teacher_uuid,
                lesson_id=lesson_to_assign.id,
                created_at=datetime.now(timezone.utc),
            )
            db.add(class_instance)
            db.commit()

            # Create attendance for 2-4 students
            num_students = min(4, len(all_student_uuids))
            for student_id in all_student_uuids[:num_students]:
                attendance = FactAttendance(
                    user_uuid=student_id,
                    class_id=class_obj.id,
                    class_instance_id=class_instance.id,
                    user_role_id=student_user_role.id,
                    attendance_date=attendance_date,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(attendance)
                db.commit()
                attendance_records.append(attendance)

    print(f"   ✅ Created {len(attendance_records)} attendance records")

    # ===== 9. CREATE FEEDBACK =====
    print("\n💬 Creating Feedback Entries...")

    feedback_comments_positive = [
        "Great class! Learned a lot about guard passing.",
        "Excellent instruction. The details really helped.",
        "Really enjoyed this session. Looking forward to the next one!",
        "John is an awesome teacher. Very patient and clear.",
        "Best class of the week! Feeling more confident now.",
    ]

    feedback_comments_negative = [
        "Class was a bit too fast-paced for me.",
        "Could use more time on drilling.",
        "Would prefer more explanation before live rolling.",
    ]

    # Create mix of positive and negative feedback (80% positive, 20% negative)
    feedback_count = 0
    for i, attendance in enumerate(
        attendance_records[:15]
    ):  # First 15 attendance records
        is_positive = i % 5 != 0  # Every 5th is negative

        feedback = ClassFeedback(
            user_uuid=attendance.user_uuid,
            attendance_id=attendance.id,
            class_instance_id=attendance.class_instance_id,
            rating="thumbs_up" if is_positive else "thumbs_down",
            comment=feedback_comments_positive[i % len(feedback_comments_positive)]
            if is_positive
            else feedback_comments_negative[i % len(feedback_comments_negative)],
            created_at=datetime.now(timezone.utc) - timedelta(days=7 - i),
        )
        db.add(feedback)
        db.commit()
        feedback_count += 1

    print(f"   ✅ Created {feedback_count} feedback entries")

    # ===== SUMMARY =====
    print("\n" + "=" * 60)
    print("🎉 SEED DATA CREATION COMPLETE!")
    print("=" * 60)

    print("\n📊 SUMMARY:")
    print(
        f"   Users: {len(all_student_uuids) + 2} (1 admin, 1 teacher, {len(all_student_uuids)} students)"
    )
    print(f"   Gyms: 2")
    print(f"   Class Types: 3")
    print(f"   Scheduled Classes: {len(created_classes)}")
    print(f"   Terms: 1")
    print(f"   Term Targets: 5 (one per rank)")
    print(f"   Curriculum: 1")
    print(f"   Lessons: {len(created_lessons)}")
    print(f"   Attendance Records: {len(attendance_records)}")
    print(f"   Feedback Entries: {feedback_count}")

    print("\n🔑 TEST CREDENTIALS:")
    print("   Admin:   admin@ckb.com   / admin123")
    print("   Teacher: teacher@ckb.com / teacher123")
    print("   Student: student@ckb.com / student123")

    print("\n📝 ADDITIONAL STUDENTS:")
    for first, last, _ in student_names:
        print(f"   {first} {last}: {first.lower()}.{last.lower()}@ckb.com / student123")

    print("\n✨ You can now:")
    print("   1. Login as teacher and view feedback (anonymous)")
    print("   2. Login as admin and view comprehensive analytics")
    print("   3. View attendance records on main page")
    print("   4. Test all filters and charts")
    print("   5. Export CSV from admin analytics")

    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n❌ Error creating seed data: {e}")
    import traceback

    traceback.print_exc()
    db.rollback()
finally:
    db.close()
