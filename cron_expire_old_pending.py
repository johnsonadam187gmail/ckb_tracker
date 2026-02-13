"""
Cron Job Script for Mat-Side Workflow

This script is designed to be run every hour to clean up old pending check-ins.
Run this via Windows Task Scheduler (Windows) or cron (Unix/Mac).

Usage:
    python cron_expire_old_pending.py

For Windows Task Scheduler:
    - Program: python
    - Arguments: cron_expire_old_pending.py
    - Start in: C:\path\to\ckb_tracker
    - Trigger: Every 1 hour

For Unix/Mac cron:
    0 * * * * /usr/bin/python3 /path/to/ckb_tracker/cron_expire_old_pending.py >> /var/log/ckb_cron.log 2>&1
"""

import requests
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configuration
BASE_URL = "http://127.0.0.1:8000"
LOG_FILE = Path("logs/cron_expire.log")


# Setup logging
def setup_logging():
    """Configure logging for cron job."""
    log_dir = LOG_FILE.parent
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger(__name__)


def main():
    """Main cron job function."""
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("Starting expire-old cron job")
    logger.info("=" * 60)

    try:
        # Call the expire-old endpoint
        response = requests.post(f"{BASE_URL}/attendance/expire-old", timeout=30)

        if response.status_code == 200:
            data = response.json()
            deleted_count = data.get("deleted_count", 0)
            message = data.get("message", "Unknown")

            logger.info(f"✅ Success: {message}")
            logger.info(f"   Deleted count: {deleted_count}")

            if deleted_count > 0:
                logger.info(f"🧹 Cleaned up {deleted_count} expired pending check-ins")
            else:
                logger.info("ℹ️  No expired check-ins to clean up")

        else:
            error_detail = response.json().get("detail", "Unknown error")
            logger.error(
                f"❌ API Error (Status {response.status_code}): {error_detail}"
            )
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        logger.error("❌ Connection Error: Could not connect to FastAPI server")
        logger.error("   Make sure the server is running on http://127.0.0.1:8000")
        sys.exit(1)
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout Error: Request took too long")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {str(e)}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Cron job completed successfully")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
