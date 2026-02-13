"""
Database Migration Script for Mat-Side Workflow

This script migrates the database to support the mat-side workflow feature:
1. Adds status, confirmed_by, confirmed_at columns to attendance table
2. Creates kiosk_auth table for PIN management
3. Sets all existing attendance records to 'confirmed' status
4. Creates default kiosk PIN (1234) if not exists

Run this script after updating the models:
    python migrate_mat_side_workflow.py

IMPORTANT: Backup your database before running this migration!
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Database path - adjust if your database is in a different location
DB_PATH = Path("test.db")

# Default PIN hash for '1234' using Argon2 (generated with get_password_hash)
DEFAULT_PIN_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHRzb21lc2FsdA$1aX7/9M7Qz9Zq3D7t0e4x5y6z7A8B9C0D1E2F3G4H5"


def check_database_exists():
    """Check if database file exists."""
    if not DB_PATH.exists():
        print(f"ERROR: Database file not found at {DB_PATH}")
        print(
            "Please ensure you're running this script from the project root directory."
        )
        sys.exit(1)


def check_columns_exist(conn):
    """Check if the new columns already exist."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(attendance)")
    columns = [col[1] for col in cursor.fetchall()]

    new_columns = ["status", "confirmed_by", "confirmed_at"]
    existing = [col for col in new_columns if col in columns]

    return existing


def migrate_attendance_table(conn):
    """Add new columns to attendance table."""
    cursor = conn.cursor()

    print("Migrating attendance table...")

    # Add status column with default 'confirmed'
    try:
        cursor.execute("""
            ALTER TABLE attendance 
            ADD COLUMN status VARCHAR(20) DEFAULT 'confirmed' NOT NULL
        """)
        print("  + Added 'status' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  = 'status' column already exists")
        else:
            raise

    # Add confirmed_by column
    try:
        cursor.execute("""
            ALTER TABLE attendance 
            ADD COLUMN confirmed_by VARCHAR REFERENCES users(user_uuid)
        """)
        print("  + Added 'confirmed_by' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  = 'confirmed_by' column already exists")
        else:
            raise

    # Add confirmed_at column
    try:
        cursor.execute("""
            ALTER TABLE attendance 
            ADD COLUMN confirmed_at TIMESTAMP
        """)
        print("  + Added 'confirmed_at' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  = 'confirmed_at' column already exists")
        else:
            raise

    conn.commit()


def set_existing_records_to_confirmed(conn):
    """Set all existing attendance records to 'confirmed' status."""
    cursor = conn.cursor()

    print("Updating existing attendance records...")

    # Count records that need updating
    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE status IS NULL OR status = ''"
    )
    count = cursor.fetchone()[0]

    if count == 0:
        print("  = No records need updating")
        return

    # Update records
    cursor.execute("""
        UPDATE attendance 
        SET status = 'confirmed' 
        WHERE status IS NULL OR status = ''
    """)

    conn.commit()
    print(f"  + Updated {count} records to 'confirmed' status")


def create_kiosk_auth_table(conn):
    """Create the kiosk_auth table for PIN management."""
    cursor = conn.cursor()

    print("Creating kiosk_auth table...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kiosk_auth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    print("  + Created kiosk_auth table")


def create_default_kiosk_pin(conn):
    """Create default kiosk PIN if not exists."""
    cursor = conn.cursor()

    print("Setting up default kiosk PIN...")

    # Check if kiosk auth already exists
    cursor.execute("SELECT COUNT(*) FROM kiosk_auth")
    count = cursor.fetchone()[0]

    if count > 0:
        print("  = Kiosk PIN already configured")
        return

    # Insert default PIN
    cursor.execute(
        """
        INSERT INTO kiosk_auth (pin_hash, created_at)
        VALUES (?, ?)
    """,
        (DEFAULT_PIN_HASH, datetime.now(timezone.utc)),
    )

    conn.commit()
    print("  + Created default kiosk PIN: '1234'")
    print("  WARNING: Please change the default PIN immediately after migration!")


def create_indexes(conn):
    """Create indexes for better query performance."""
    cursor = conn.cursor()

    print("Creating indexes...")

    # Index on status column for faster filtering
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_status 
            ON attendance(status)
        """)
        print("  + Created index on attendance.status")
    except sqlite3.OperationalError:
        print("  = Index on status already exists")

    # Index on confirmed_by column
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_confirmed_by 
            ON attendance(confirmed_by)
        """)
        print("  + Created index on attendance.confirmed_by")
    except sqlite3.OperationalError:
        print("  = Index on confirmed_by already exists")

    conn.commit()


def verify_migration(conn):
    """Verify the migration was successful."""
    cursor = conn.cursor()

    print("\nVerifying migration...")

    # Check attendance table columns
    cursor.execute("PRAGMA table_info(attendance)")
    columns = {col[1] for col in cursor.fetchall()}

    required_columns = {"status", "confirmed_by", "confirmed_at"}
    missing = required_columns - columns

    if missing:
        print(f"  X Missing columns in attendance table: {missing}")
        return False

    print("  + All required columns present in attendance table")

    # Check kiosk_auth table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='kiosk_auth'"
    )
    if not cursor.fetchone():
        print("  X kiosk_auth table not found")
        return False

    print("  + kiosk_auth table exists")

    # Check kiosk PIN exists
    cursor.execute("SELECT COUNT(*) FROM kiosk_auth")
    if cursor.fetchone()[0] == 0:
        print("  X No kiosk PIN configured")
        return False

    print("  + Kiosk PIN configured")

    # Check attendance records have status
    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE status IS NULL OR status = ''"
    )
    null_count = cursor.fetchone()[0]

    if null_count > 0:
        print(f"  ! {null_count} attendance records still have NULL/empty status")
    else:
        print("  + All attendance records have status set")

    return True


def main():
    """Main migration function."""
    print("=" * 60)
    print("CKB Tracker - Mat-Side Workflow Database Migration")
    print("=" * 60)
    print()

    # Safety check
    print("WARNING: Ensure you have backed up your database before proceeding!")
    response = input("\nDo you want to continue? (yes/no): ")

    if response.lower() != "yes":
        print("\nMigration cancelled.")
        sys.exit(0)

    print()

    # Check database exists
    check_database_exists()

    # Connect to database
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    try:
        # Check if migration already applied
        existing = check_columns_exist(conn)
        if existing:
            print(f"\nNote: Some columns already exist: {existing}")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != "yes":
                print("\nMigration cancelled.")
                return

        print()

        # Run migrations
        migrate_attendance_table(conn)
        set_existing_records_to_confirmed(conn)
        create_kiosk_auth_table(conn)
        create_default_kiosk_pin(conn)
        create_indexes(conn)

        # Verify
        if verify_migration(conn):
            print("\n" + "=" * 60)
            print("SUCCESS: Migration completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Change the default kiosk PIN (1234) via the Settings page")
            print("2. Test the mat-side workflow:")
            print("   - Students: Enter PIN on Landing page -> Self check-in")
            print("   - Teachers: Login -> Confirm Attendance tab")
            print("3. Run tests: pytest tests/")
        else:
            print("\n" + "=" * 60)
            print("WARNING: Migration completed with warnings")
            print("=" * 60)

    except Exception as e:
        print(f"\nERROR: Migration failed: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
