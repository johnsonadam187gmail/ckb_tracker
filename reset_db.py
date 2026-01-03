# Create a temporary file called reset_db.py
from app.database import engine
from app.models import Base

# This will delete EVERYTHING in your database!
Base.metadata.drop_all(bind=engine)

# This will recreate the tables with your NEW columns
Base.metadata.create_all(bind=engine)

print("Database reset successfully with new columns!")