# Technology Stack

**Analysis Date:** 2026-02-11

## Languages

**Primary:**
- Python 3.14.2 - Core application language for backend and frontend

**Secondary:**
- SQL - Database queries via SQLAlchemy ORM
- CSS - Custom styling in `assets/` directory
- Markdown - Documentation

## Runtime

**Environment:**
- Python 3.14.2

**Package Manager:**
- pip (standard Python package manager)
- uv (universal Python package manager, lockfile present: `uv.lock`)

## Frameworks

**Core:**
- FastAPI 0.127.0+ - REST API backend framework
- Streamlit 1.52.2+ - Interactive web frontend framework
- SQLAlchemy 2.0.45+ - ORM and database abstraction layer
- Pydantic 2.12.5+ (with email support) - Data validation and schemas

**Testing:**
- pytest - Test framework (11 test files in `tests/` directory)
- pytest-cov - Coverage reporting

**Build/Dev:**
- Uvicorn 0.40.0+ (with standard extras) - ASGI server for FastAPI
- python-dotenv 1.2.1+ - Environment variable management

## Key Dependencies

**Critical:**
- fastapi 0.127.0+ - API framework with automatic OpenAPI docs
- sqlalchemy 2.0.45+ - ORM for database operations with SCD Type 2 support
- streamlit 1.52.2+ - Frontend UI framework
- pydantic 2.12.5+ - Schema validation with email validation support
- uvicorn 0.40.0+ - Production ASGI server

**Authentication & Security:**
- passlib 1.7.4+ (with bcrypt) - Password hashing with Argon2 support
- python-jose[cryptography] - JWT token generation and validation
- python-multipart 0.0.21+ - Form data and file upload handling

**Cloud Services:**
- cloudinary 1.36.0+ - Cloud-based image storage and processing
- Pillow 10.0.0+ - Image processing (resizing, format conversion, EXIF handling)

**Data & Analytics:**
- pandas 2.3.3+ - Data manipulation and CSV export
- plotly 6.5.0+ - Interactive charts for analytics dashboard
- python-dateutil 2.9.0.post0+ - Date parsing utilities

**Database:**
- psycopg2-binary 2.9.11+ - PostgreSQL adapter (production ready)
- SQLite - Default development database (via Python stdlib)

**Google Integration (Installed but Not Currently Used):**
- google-api-python-client 2.187.0+ - Google API client library
- google-auth-httplib2 0.3.0+ - Google Auth HTTP transport
- google-auth-oauthlib 1.2.3+ - Google OAuth 2.0 support

## Configuration

**Environment:**
- `.env` file for secrets and configuration (gitignored)
- `.env.example` template provided
- `app/config.py` - Settings class loads environment variables
- Environment variables: DATABASE_URL, API_HOST, API_PORT, CLOUDINARY credentials, SECRET_KEY

**Build:**
- `pyproject.toml` - Project metadata and dependencies
- `uv.lock` - Locked dependency versions
- `.streamlit/config.toml` - Streamlit theme and server configuration

**Key Configs:**
- Database: Configurable via `DATABASE_URL` (defaults to SQLite `test.db`)
- File uploads: `UPLOAD_DIR` (defaults to `static/profile_pics/`)
- Cloudinary: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- JWT: `SECRET_KEY` (auto-generated if missing)
- Logging: `LOG_LEVEL` (defaults to INFO)

## Platform Requirements

**Development:**
- Python 3.12+ (running 3.14.2)
- Virtual environment (`.venv/` directory present)
- SQLite 3 (bundled with Python)
- 5MB max file upload size (configurable)

**Production:**
- ASGI server: Uvicorn with standard extras (production-ready)
- Database: SQLite (dev) or PostgreSQL (production via DATABASE_URL)
- Cloud Storage: Cloudinary account for profile photos
- Port 8000: FastAPI backend
- Port 8501: Streamlit frontend

---

*Stack analysis: 2026-02-11*
