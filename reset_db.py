# Create a temporary file called reset_db.py
from app.database import engine, SessionLocal
from app.models import Base, Role

# This will delete EVERYTHING in your database!
Base.metadata.drop_all(bind=engine)

# This will recreate the tables with your NEW columns
Base.metadata.create_all(bind=engine)

# Seed roles
db = SessionLocal()
try:
    roles = [
        Role(name="Student", description="Member attending classes"),
        Role(name="Teacher", description="Instructor teaching classes"),
        Role(name="Admin", description="Administrator with full access"),
    ]
    for role in roles:
        db.add(role)
    db.commit()
    print("Database reset successfully with new columns!")
    print("Seeded 3 roles: Student, Teacher, Admin")
except Exception as e:
    print(f"Error seeding roles: {e}")
    db.rollback()
finally:
    db.close()
