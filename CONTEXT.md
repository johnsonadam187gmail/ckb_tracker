opencode chat "ACT AS A SENIOR FULL-STACK DEVELOPER. 

GOAL: Rebuild the 'CKB Tracker' Attendance App from scratch with a modular, scalable architecture.

ENTITIES TO CREATE:
1. ROLES: Static table (Admin, Teacher, Student).
2. USERS: Link to Roles (Many-to-Many). Fields: uuid, name, email, hashed_password, created_at.
3. RANKS/BELTS: A table defining progression levels (e.g., White, Blue, Purple, Brown, Black).
4. ATTENDANCE: Logs linking User + Timestamp + ClassType.
5. CLASSES: Schedule/Session info.

TECHNICAL REQUIREMENTS:
- BACKEND: FastAPI + SQLAlchemy. Use a /routes folder for modularity.
- DATABASE: SQLite. Ensure 'Student' role is assigned by default upon registration.
- SCHEMAS: Use Pydantic v2 for all Request/Response models.
- FRONTEND: Streamlit with a clear 'Teacher Dashboard' vs 'Student View'.

INSTRUCTIONS:
1. Provide the complete code for 'app/models.py'.
2. Provide the database initialization script to seed the 3 Roles.
3. Standardize the API endpoints in 'app/main.py'.
4. Ensure the User update logic handles role changes without IntegrityErrors.

DO NOT write partial code. Provide the full file structures." --model openrouter/google/gemini-2.5-pro

## UI Features
- **Modern Glassmorphism Design**: Translucent elements with backdrop blur for depth and elegance
- **Dynamic Theme Toggle**: Light/dark mode switching with persistent state across all pages
- **Smooth Animations**: Hover effects, ripple clicks, page transitions, and toast notifications
- **Responsive Layout**: Mobile-friendly design with 768px breakpoint optimization
- **CKB Branding**: Red primary color (#c91a2b), Inter font family, professional color palette
- **Accessibility**: WCAG AA compliant contrast ratios, clear focus states, semantic color usage