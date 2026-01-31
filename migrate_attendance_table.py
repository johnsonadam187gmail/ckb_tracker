"""
Migration script to update attendance table with new columns.
SQLite doesn't support adding foreign key columns, so we need to recreate the table.
Run once: python migrate_attendance_table.py
"""

import sys
import io
from app.database import SessionLocal, engine
from app import models
import sqlite3

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def migrate():
    print("Migrating attendance table to add teacher_uuid and user_role_id...")
    print("=" * 60)

    # Use raw SQLite connection for complex migrations
    conn = sqlite3.connect("test.db")
    cursor = conn.cursor()

    try:
        # 1. Check if columns already exist
        cursor.execute("PRAGMA table_info(attendance)")
        columns = [row[1] for row in cursor.fetchall()]

        if "teacher_uuid" in columns and "user_role_id" in columns:
            print("[INFO] Columns already exist. No migration needed.")
            return

        print("\n1. Backing up existing attendance data...")
        cursor.execute("SELECT * FROM attendance")
        old_data = cursor.fetchall()
        print(f"   [OK] Backed up {len(old_data)} records")

        # 2. Get old column names
        cursor.execute("PRAGMA table_info(attendance)")
        old_columns = cursor.fetchall()
        old_column_names = [col[1] for col in old_columns]
        print(f"   [OK] Old columns: {', '.join(old_column_names)}")

        # 3. Rename old table
        print("\n2. Renaming old table...")
        cursor.execute("ALTER TABLE attendance RENAME TO attendance_old")
        print("   [OK] Renamed to attendance_old")

        # 4. Create new table with new schema
        print("\n3. Creating new attendance table...")
        cursor.execute("""
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uuid TEXT NOT NULL,
                class_id INTEGER NOT NULL,
                teacher_uuid TEXT,
                user_role_id INTEGER,
                attendance_date DATE,
                created_at TIMESTAMP,
                FOREIGN KEY (user_uuid) REFERENCES users(user_uuid),
                FOREIGN KEY (class_id) REFERENCES classes(id),
                FOREIGN KEY (teacher_uuid) REFERENCES users(user_uuid),
                FOREIGN KEY (user_role_id) REFERENCES user_roles(id),
                UNIQUE (user_uuid, class_id, attendance_date)
            )
        """)
        print("   [OK] New table created")

        # 5. Copy data from old table
        print("\n4. Copying data from old table...")
        cursor.execute("""
            INSERT INTO attendance (id, user_uuid, class_id, attendance_date, created_at)
            SELECT id, user_uuid, class_id, attendance_date, created_at
            FROM attendance_old
        """)
        print(f"   [OK] Copied {len(old_data)} records")

        # 6. Drop old table
        print("\n5. Dropping old table...")
        cursor.execute("DROP TABLE attendance_old")
        print("   [OK] Old table dropped")

        # 7. Create indexes
        print("\n6. Creating indexes...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_attendance_user_uuid ON attendance(user_uuid)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_attendance_teacher_uuid ON attendance(teacher_uuid)"
        )
        print("   [OK] Indexes created")

        conn.commit()

        print("\n" + "=" * 60)
        print("[SUCCESS] Attendance table migration complete!")
        print("[INFO] teacher_uuid and user_role_id columns added")
        print("[INFO] Existing records have NULL for these fields")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
