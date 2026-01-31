"""
Application configuration loaded from environment variables.
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """Application settings with environment variable support."""

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")

    # API Configuration
    api_title: str = os.getenv("API_TITLE", "CKB Attendance Tracking System")
    api_version: str = "0.1.0"
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # File Upload
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "static/profile_pics"))
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))

    # Frontend
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:8501")

    # Security (for future use)
    secret_key: Optional[str] = os.getenv("SECRET_KEY")
    admin_username: Optional[str] = os.getenv("ADMIN_USERNAME")
    admin_password: Optional[str] = os.getenv("ADMIN_PASSWORD")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


# Global settings instance
settings = Settings()

# Ensure upload directory exists
settings.upload_dir.mkdir(parents=True, exist_ok=True)
