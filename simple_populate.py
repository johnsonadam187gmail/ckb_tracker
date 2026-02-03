"""
Simple populate script with no emojis.
Populates the database with sample data for testing.
"""

from datetime import datetime, timezone, date, timedelta
import uuid
import random
from sqlalchemy.orm import Session
from app import models
from app.database import get_db, engine


def create_sample_users(db: Session):
    """Create sample users with various ranks"""
    print("\nCreating sample users...")

    # Create users with different ranks
    users_data = [
        {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@example.com",
            "rank": "White",
        },
        {
            "first_name": "Emily",
            "last_name": "Johnson",
            "email": "emily.j@example.com",
            "rank": "Blue",
        },
        {
            "first_name": "Michael",
            "last_name": "Williams",
            "email": "mike.w@example.com",
            "rank": "Purple",
        },
        {
            "first_name": "Sarah",
            "last_name": "Brown",
            "email": "sarah.b@example.com",
            "rank": "Brown",
        },
        {
            "first_name": "David",
            "last_name": "Jones",
            "email": "david.j@example.com",
            "rank": "Black",
        },
    ]

    created_users = []
    for user_data in users_data:
        user_uuid = str(uuid.uuid4())
        new_user = models.User(
            user_uuid=user_uuid,
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            email=user_data["email"],
            rank=user_data["rank"],
            is_current=True,
            created_date=datetime.now(timezone.utc),
            effective_date=datetime.now(timezone.utc),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"  Created user: {user_data['first_name']} {user_data['last_name']}")

        # Assign roles (all are Students, the last two are also Teachers)
        student_role = (
            db.query(models.Role).filter(models.Role.name == "Student").first()
        )
        student_ur = models.UserRole(
            user_uuid=user_uuid,
            role_id=student_role.id,
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        db.add(student_ur)

        # Make David and Sarah teachers
        if user_data["first_name"] in ["David", "Sarah"]:
            teacher_role = (
                db.query(models.Role).filter(models.Role.name == "Teacher").first()
            )
            teacher_ur = models.UserRole(
                user_uuid=user_uuid,
                role_id=teacher_role.id,
                is_current=True,
                effective_date=datetime.now(timezone.utc),
                created_date=datetime.now(timezone.utc),
            )
            db.add(teacher_ur)
            print(f"  {user_data['first_name']} is also a Teacher")

        created_users.append(new_user)

    db.commit()
    return created_users


def create_sample_classes(db: Session):
    """Create sample classes"""
    print("\nCreating sample classes...")

    # First create gym location
    gym = models.GymLocation(name="CKB Downtown", address="123 Main St")
    db.add(gym)
    db.commit()

    # Create class types
    class_types = [
        models.ClassType(name="Gi"),
        models.ClassType(name="No-Gi"),
        models.ClassType(name="Fundamentals"),
    ]
    db.add_all(class_types)
    db.commit()

    classes_data = [
        {
            "class_name": "Fundamentals 1",
            "class_type_id": class_types[2].id,  # Fundamentals
            "gym_id": gym.id,
            "day": "Monday",
            "time": "18:00",
            "points": 1.0,
        },
        {
            "class_name": "Advanced Gi",
            "class_type_id": class_types[0].id,  # Gi
            "gym_id": gym.id,
            "day": "Wednesday",
            "time": "19:00",
            "points": 1.5,
        },
        {
            "class_name": "No-Gi Competition",
            "class_type_id": class_types[1].id,  # No-Gi
            "gym_id": gym.id,
            "day": "Friday",
            "time": "18:30",
            "points": 1.5,
        },
    ]

    created_classes = []
    for class_data in classes_data:
        class_uuid = str(uuid.uuid4())
        new_class = models.ClassSchedule(
            class_uuid=class_uuid,
            class_name=class_data["class_name"],
            class_type_id=class_data["class_type_id"],
            gym_id=class_data["gym_id"],
            day=class_data["day"],
            time=class_data["time"],
            points=class_data["points"],
            is_current=True,
            effective_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
        )
        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        print(f"  Created class: {class_data['class_name']}")
        created_classes.append(new_class)

    return created_classes


def create_sample_attendance(db: Session, users, classes):
    """Create sample attendance records"""
    print("\nCreating attendance records...")

    # Create attendance records over the past 30 days
    today = date.today()

    # Get teacher
    teacher = next(u for u in users if u.first_name == "David")
    teacher_uuid = teacher.user_uuid

    # Get teacher role ID
    teacher_role_id = (
        db.query(models.UserRole)
        .filter(
            models.UserRole.user_uuid == teacher_uuid,
            models.UserRole.is_current == True,
        )
        .first()
        .id
    )

    attendance_records = []
    class_instances = {}

    # Create attendance for different users on different days
    for i in range(30):
        class_date = today - timedelta(days=i)

        # Select random class
        selected_class = random.choice(classes)

        # Create or get class instance
        instance_key = (selected_class.id, class_date)
        if instance_key not in class_instances:
            class_instance = models.ClassInstance(
                class_id=selected_class.id,
                class_date=class_date,
                teacher_uuid=teacher_uuid,  # David is the teacher
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(class_instance)
            db.commit()
            db.refresh(class_instance)
            class_instances[instance_key] = class_instance
        else:
            class_instance = class_instances[instance_key]

        # Create attendance for 1-3 random users
        num_attendees = random.randint(1, 3)
        selected_users = random.sample(users, num_attendees)

        for user in selected_users:
            # Get user's Student role
            student_role = (
                db.query(models.UserRole)
                .filter(
                    models.UserRole.user_uuid == user.user_uuid,
                    models.UserRole.is_current == True,
                    models.UserRole.role_id == 1,  # Student role ID
                )
                .first()
            )

            if not student_role:
                continue  # Skip if no Student role (shouldn't happen)

            attendance = models.FactAttendance(
                user_uuid=user.user_uuid,
                class_id=selected_class.id,
                class_instance_id=class_instance.id,
                attendance_date=class_date,
                user_role_id=student_role.id,
                created_at=datetime.now(timezone.utc),
            )

            try:
                db.add(attendance)
                db.commit()
                db.refresh(attendance)
                attendance_records.append(attendance)
                print(f"  Created attendance for {user.first_name} on {class_date}")
            except Exception as e:
                db.rollback()
                print(f"  Error: {e}")

    return attendance_records


def main():
    """Main function to populate database"""
    print("Starting database population...")
    print("=" * 60)

    db = next(get_db())

    try:
        # Create users
        users = create_sample_users(db)

        # Create classes
        classes = create_sample_classes(db)

        # Create attendance records
        attendance_records = create_sample_attendance(db, users, classes)

        print("\nDatabase population completed successfully!")
        print(f"Created {len(users)} users")
        print(f"Created {len(classes)} classes")
        print(f"Created {len(attendance_records)} attendance records")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
