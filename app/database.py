import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

# 1. Load the variables from your .env file
load_dotenv()

# 2. Get the URL from the environment variable
# If you are testing locally without a .env, it defaults to a local SQLite file
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# 3. Create the SQLAlchemy engine
# 'check_same_thread' is only needed for SQLite.
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Create a Session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Create a Base class for your models to inherit from
class Base(DeclarativeBase):
    pass

# 6. Dependency to get the database session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()