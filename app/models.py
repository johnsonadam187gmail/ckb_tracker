from .database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Float, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_uuid = Column(String, unique=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # For Auth
    rank = Column(String(50))
    last_graded_date = Column(DateTime, nullable=True)
    
    comments = Column(Text, nullable=True)
    nicknames = Column(Text, nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    # SCD TYPE 2 TRACKING
    is_current = Column(Boolean, default=True)
    effective_date = Column(DateTime, default=datetime.now(timezone.utc))
    end_date = Column(DateTime, nullable=True)

    created_date = Column(DateTime, default=datetime.now(timezone.utc))
    updated_date = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationship to attendance
    attendance_records = relationship("FactAttendance", back_populates="user")

class ClassSchedule(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    class_uuid = Column(String(50), index=True) # Anchor for the class
    class_name = Column(String(100), nullable=False)
    day = Column(String(20))
    time = Column(String(20))
    description = Column(Text)
    weighting = Column(Float, default=1.0)
    
    # SCD Tracking Columns
    is_current = Column(Boolean, default=True)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_date = Column(DateTime, nullable=True)
    created_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to attendance
    attendance_records = relationship("FactAttendance", back_populates="class_info")

class FactAttendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    
    # ADD THE FOREIGN KEY HERE 
    # It must point to 'tablename.column_name'
    user_uuid = Column(String, ForeignKey("users.user_uuid"), index=True) 
    
    class_id = Column(Integer, ForeignKey("classes.id"))
    attendance_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # This relationship now knows how to "join" because of the ForeignKey above
    user = relationship("User", back_populates="attendance_records")
    class_info = relationship("ClassSchedule", back_populates="attendance_records")