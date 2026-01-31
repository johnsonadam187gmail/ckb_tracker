"""
Migration Script: Add Curriculum System to CKB Tracker

This script:
1. Clears existing test data (acceptable per user)
2. Creates new tables (curricula, lessons)
3. Recreates class_instances with new schema (adds lesson_id FK, removes lesson content fields)
4. Auto-creates curriculum for each existing class

Run this script to upgrade the database schema.
"""

import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "test.db"


def migrate():
    print("[*] Starting database migration to Curriculum System...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Step 1: Clear existing test data
        print("\n[1] Step 1: Clearing existing test data...")
        cursor.execute("DELETE FROM attendance;")
        cursor.execute("DELETE FROM class_instances;")
        print("   [OK] Test data cleared")

        # Step 2: Create new tables
        print("\n[2] Step 2: Creating new tables...")

        # Create curricula table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS curricula (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER UNIQUE NOT NULL,
                name VARCHAR(200),
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
            );
        """)
        print("   [OK] Created 'curricula' table")

        # Create lessons table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curriculum_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                lesson_plan_url VARCHAR(500),
                video_folder_url VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (curriculum_id) REFERENCES curricula(id) ON DELETE CASCADE
            );
        """)
        print("   [OK] Created 'lessons' table")

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_curricula_class_id ON curricula(class_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lessons_curriculum_id ON lessons(curriculum_id);"
        )
        print("   [OK] Created indexes")

        # Step 3: Recreate class_instances table with new schema
        print("\n[3] Step 3: Recreating class_instances table...")

        # Drop old table
        cursor.execute("DROP TABLE IF EXISTS class_instances;")

        # Create new table with lesson_id FK
        cursor.execute("""
            CREATE TABLE class_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                class_date DATE NOT NULL,
                teacher_uuid VARCHAR(50),
                lesson_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id),
                FOREIGN KEY (teacher_uuid) REFERENCES users(user_uuid),
                FOREIGN KEY (lesson_id) REFERENCES lessons(id),
                UNIQUE (class_id, class_date)
            );
        """)
        print("   [OK] Recreated 'class_instances' with new schema")

        # Create index for lesson_id
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_class_instances_lesson_id ON class_instances(lesson_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_class_instances_class_id ON class_instances(class_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_class_instances_class_date ON class_instances(class_date);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_class_instances_teacher_uuid ON class_instances(teacher_uuid);"
        )
        print("   [OK] Created indexes for class_instances")

        # Step 4: Auto-create curricula for existing classes
        print("\n[4] Step 4: Auto-creating curricula for existing classes...")

        cursor.execute("SELECT id, class_name FROM classes WHERE is_current = 1;")
        classes = cursor.fetchall()

        if classes:
            for class_id, class_name in classes:
                curriculum_name = f"{class_name} Curriculum"
                cursor.execute(
                    """
                    INSERT INTO curricula (class_id, name, description)
                    VALUES (?, ?, ?)
                """,
                    (class_id, curriculum_name, f"Curriculum for {class_name}"),
                )
                print(f"   [OK] Created curriculum for '{class_name}'")
        else:
            print(
                "   [INFO] No classes found (curricula will be created when classes are added)"
            )

        # Commit all changes
        conn.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        print(f"\n[SUMMARY]")
        print(f"   - Created 'curricula' table")
        print(f"   - Created 'lessons' table")
        print(f"   - Recreated 'class_instances' with lesson_id FK")
        print(f"   - Auto-created {len(classes)} curriculum/curricula")
        print(f"\n[NEXT STEPS]")
        print(f"   1. Run backend server")
        print(f"   2. Use Curriculum Management page to add lessons")
        print(f"   3. Assign lessons to class dates")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
