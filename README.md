# CKB Tracker - Martial Arts Attendance Tracking System

A comprehensive attendance tracking application for martial arts classes, built with FastAPI backend and Streamlit frontend.

## 🎯 Overview

CKB Tracker is a full-featured web application designed to manage attendance, track student progression, manage class schedules, and provide analytics for martial arts training facilities. It includes role-based access control (Student, Teacher, Admin), lesson management, curriculum tracking, and comprehensive reporting.

## 🚀 Tech Stack

- **Backend**: FastAPI 0.127.0+ with Uvicorn
- **Database**: SQLite with SQLAlchemy 2.0+ ORM
- **Frontend**: Streamlit 1.52.2+
- **Validation**: Pydantic v2 (with email support)
- **Authentication**: JWT tokens with Passlib/bcrypt
- **Testing**: Pytest with comprehensive test suite

## 📋 Features

### Core Functionality
- **Attendance Tracking**: Check-in system with date/class selection
- **User Management**: Student/teacher profiles with rank tracking
- **Class Scheduling**: Recurring class schedules with points system
- **Role-Based Access**: Student, Teacher, and Admin roles with appropriate permissions

### Advanced Features
- **Curriculum Management**: Organize lessons into structured learning paths
- **Lesson Library**: Store lesson plans, video resources, and training materials
- **Teacher Assignment**: Track which teachers taught each class occurrence
- **Class Feedback**: Students can rate classes and leave comments
- **Analytics Dashboard**: 
  - Student analytics (attendance, points, target tracking)
  - Teacher analytics (classes taught, student counts)
  - Admin feedback analytics (comprehensive stats and visualizations)
- **Term/Target Management**: Set and track performance goals per training term
- **Slowly Changing Dimensions (SCD Type 2)**: Complete historical tracking for users and classes

### UI/UX
- **Modern Glassmorphism Design**: Translucent elements with backdrop blur
- **Dynamic Theme Toggle**: Light/dark mode switching
- **Responsive Layout**: Mobile-friendly design (768px breakpoint)
- **Smooth Animations**: Hover effects, ripple clicks, toast notifications
- **CKB Branding**: Red primary color (#c91a2b), Inter font family

## 🛠️ Quick Start

### Prerequisites
- Python 3.12+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ckb_tracker
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Unix/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (SECRET_KEY auto-generated if missing)
   ```

5. **Initialize database**
   ```bash
   python reset_db.py
   ```

6. **Seed test data (optional)**
   ```bash
   python seed_users.py  # Creates admin/teacher/student test accounts
   python seed_complete_data.py  # Full test dataset
   ```

### Running the Application

**Terminal 1 - Start Backend:**
```bash
uvicorn app.main:app --reload
```
Backend runs on http://127.0.0.1:8000

**Terminal 2 - Start Frontend:**
```bash
streamlit run Attendance.py
```
Frontend runs on http://localhost:8501

### Test Accounts (after running seed_users.py)
- **Admin**: admin@ckb.com / admin123
- **Teacher**: teacher@ckb.com / teacher123
- **Student**: student@ckb.com / student123

## 📁 Project Structure

```
ckb_tracker/
├── app/                      # Backend application
│   ├── routers/             # API route modules (auth, users, classes, etc.)
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── database.py          # Database connection & session management
│   ├── auth.py              # JWT authentication utilities
│   └── main.py              # FastAPI application entry point
├── pages/                    # Streamlit additional pages
│   ├── 2_Analytics.py       # Student/teacher analytics dashboard
│   ├── 3_Settings.py        # Admin settings (users, classes, curricula, etc.)
│   ├── 4_Teacher.py         # Teacher dashboard (roster, feedback, assignments)
│   └── 5_Student_Analytics.py # Student-specific analytics and feedback
├── assets/                   # UI styling
│   ├── style.css            # Main component styles
│   ├── dark-theme.css       # Dark mode color palette
│   └── light-theme.css      # Light mode color palette
├── tests/                    # Pytest test suite
│   ├── test_*.py            # Unit and integration tests
│   └── __init__.py
├── static/                   # Static assets
│   └── profile_pics/        # User profile images
├── utils/                    # Utility modules
│   └── api_client.py        # API client for frontend
├── .streamlit/              # Streamlit configuration
│   └── config.toml          # Theme and server settings
├── Attendance.py            # Main Streamlit app (home page)
├── reset_db.py              # Database reset utility
├── seed_users.py            # Seed test user accounts
├── seed_complete_data.py    # Seed comprehensive test data
├── pyproject.toml           # Project dependencies
├── test.db                  # SQLite database (development)
├── AGENTS.md                # Comprehensive development guide
└── README.md                # This file
```

## 🧪 Testing

Run the test suite with pytest:

```bash
# Install pytest
pip install pytest pytest-cov

# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=app tests/
```

## 🔧 Development

### Database Operations

**Reset database** (drops all tables and recreates):
```bash
python reset_db.py
```

**Create test accounts**:
```bash
python seed_users.py
```

**Populate full test dataset**:
```bash
python seed_complete_data.py
```

### Code Style Guidelines

- **Import Order**: Standard library → Third-party → Local imports
- **Type Hints**: Always use type hints for function parameters and return values
- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes
- **Database Patterns**: SCD Type 2 for historical tracking, UUID anchors for stable identifiers
- **Error Handling**: Use `HTTPException` for API errors, always rollback database errors

See **AGENTS.md** for comprehensive development guidelines, API conventions, and architectural patterns.

## 📊 Database Models

### Core Entities
- **User**: Members with SCD Type 2 versioning and password authentication
- **Role**: Fixed roles (Student, Teacher, Admin)
- **UserRole**: Many-to-many user-role assignments with historical tracking
- **ClassSchedule**: Recurring classes with SCD Type 2 versioning
- **ClassInstance**: Specific class occurrence (class + date + teacher + lesson)
- **FactAttendance**: Attendance records linked to class instances
- **Curriculum**: Lesson collections per class (1:1 relationship)
- **Lesson**: Reusable training content (plans, videos, descriptions)
- **ClassFeedback**: Student feedback on class instances
- **Term**: Training terms/semesters
- **TermTarget**: Performance targets per rank per term
- **GymLocation**: Training locations
- **ClassType**: Class categories (Gi, No-Gi, etc.)

### Key Design Patterns
- **SCD Type 2**: Historical tracking with `is_current`, `effective_date`, `end_date`
- **UUID Anchors**: `user_uuid` and `class_uuid` for stable cross-version references
- **Role System**: Many-to-many with complete historical tracking
- **Curriculum Management**: Structured lesson organization and assignment

## 🔐 Authentication

- **JWT Tokens**: 5-minute expiry with rolling window extension
- **Password Hashing**: Argon2 via passlib
- **Role-Based Access**: Teacher dashboard requires Teacher role
- **Session Management**: Automatic logout on token expiry

## 📱 Frontend Pages

1. **Attendance (Home)**: Student check-in with date/class selection
2. **Analytics**: Role-aware dashboard (student or teacher analytics)
3. **Settings**: Admin panel for user/class/curriculum management
4. **Teacher Dashboard**: Class roster, teacher assignments, lesson info, feedback
5. **Student Analytics**: Personal attendance tracking and feedback submission

## 🎨 UI Theming

The application uses a hybrid light/dark theme system with:
- CSS variable-based theming
- Glassmorphism design patterns
- Smooth animations and transitions
- Responsive design with mobile breakpoints
- CKB red branding (#c91a2b)

See **AGENTS.md** → "UI Styling Guidelines" for detailed theming documentation.

## 📚 API Documentation

Once the backend is running, visit:
- **Interactive API Docs**: http://127.0.0.1:8000/docs
- **Alternative Docs**: http://127.0.0.1:8000/redoc

## 🤝 Contributing

This project follows strict development guidelines outlined in **AGENTS.md**:

1. **Definition of Done**: Written → Linted → Verified → Tested
2. **Test First**: Develop tests alongside features
3. **Database Patterns**: Follow SCD Type 2 conventions
4. **Type Safety**: Always use type hints
5. **Documentation**: Update AGENTS.md for architectural changes

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Built for martial arts training facilities to streamline attendance tracking and student progression management.

---

**For detailed development guidelines, API conventions, and architectural patterns, see [AGENTS.md](AGENTS.md)**
