#!/usr/bin/env python3
"""
CKB Tracker Database Backup Script

This script creates a backup of the SQLite database.
Can be run manually or scheduled via cron.

Usage:
    python scripts/backup_db.py
    python scripts/backup_db.py --output /path/to/backup.db
    python scripts/backup_db.py --compress

For cron scheduling (daily at 2 AM):
    0 2 * * * cd /path/to/ckb_tracker && python scripts/backup_db.py
"""

import shutil
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


def create_backup(output_path: Path = None, compress: bool = False) -> Path:
    """Create a backup of the database file.

    Args:
        output_path: Optional custom output path
        compress: Whether to compress the backup as zip

    Returns:
        Path to the created backup file
    """
    # Get database path from config
    db_url = settings.database_url

    if not db_url.startswith("sqlite"):
        print("❌ Backup only supported for SQLite databases")
        print(f"   Current database: {db_url}")
        sys.exit(1)

    # Extract database file path from URL
    db_path = Path(db_url.replace("sqlite:///", "").replace("sqlite://", ""))

    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)

    # Determine backup path
    if output_path:
        backup_path = output_path
    else:
        # Default: backups/ directory with timestamp
        backup_dir = Path(__file__).parent.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"backup_{timestamp}.db"

    # Ensure backup directory exists
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy database file
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup created: {backup_path}")

        # Get file size
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"   Size: {size_mb:.2f} MB")

        # Compress if requested
        if compress:
            import zipfile

            zip_path = backup_path.with_suffix(".db.zip")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(backup_path, backup_path.name)

            # Remove uncompressed backup
            backup_path.unlink()
            backup_path = zip_path

            zip_size_mb = backup_path.stat().st_size / (1024 * 1024)
            print(f"✅ Compressed: {backup_path}")
            print(f"   Compressed size: {zip_size_mb:.2f} MB")
            print(f"   Compression: {(1 - zip_size_mb / size_mb) * 100:.1f}%")

        return backup_path

    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        sys.exit(1)


def list_backups():
    """List all available backups."""
    backup_dir = Path(__file__).parent.parent / "backups"

    if not backup_dir.exists():
        print("No backups directory found")
        return

    backups = sorted(
        backup_dir.glob("backup_*.db*"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not backups:
        print("No backups found")
        return

    print(f"\n📦 Found {len(backups)} backup(s):\n")
    print(f"{'Date':<20} {'Size':<12} {'File':<30}")
    print("-" * 62)

    for backup in backups:
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        size_mb = backup.stat().st_size / (1024 * 1024)
        print(
            f"{mtime.strftime('%Y-%m-%d %H:%M'):<20} {size_mb:>8.2f} MB   {backup.name:<30}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Create backup of CKB Tracker database"
    )
    parser.add_argument(
        "-o", "--output", type=Path, help="Custom output path for backup file"
    )
    parser.add_argument(
        "-c", "--compress", action="store_true", help="Compress backup as zip file"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List all available backups"
    )

    args = parser.parse_args()

    if args.list:
        list_backups()
    else:
        backup_path = create_backup(args.output, args.compress)
        print(f"\n✅ Backup complete: {backup_path}")


if __name__ == "__main__":
    main()
