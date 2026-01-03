from .database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Float, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_uuid = Column(String, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # For Auth
    rank = Column(String(50))
    last_graded_date = Column(DateTime, nullable=True)
    
    comments = Column(Text, nullable=True)
    nicknames = Column(Text, nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    # SCD TYPE 2 TRACKING
    is_current = Column(Boolean, default=True)
    effective_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)

    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to attendance
    attendance_records = relationship("FactAttendance", back_populates="user")

class ClassSchedule(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String(100), nullable=False)
    day = Column(String(20))  # e.g., "Monday"
    time = Column(String(20)) # e.g., "18:30"
    description = Column(Text)
    weighting = Column(Float, default=1.0) # For Analytics
    created_date = Column(DateTime, default=datetime.utcnow)

    # Relationship to attendance
    attendance_records = relationship("FactAttendance", back_populates="class_info")

class FactAttendance(Base):
    __tablename__ = "fact_attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    attendance_datetime = Column(DateTime, default=datetime.utcnow)
    
    # Status allows for 'Present', 'Late', or 'Excused'
    # Only records existing here count as 'engagement'
    status = Column(String(20), default="Present") 

    user = relationship("User", back_populates="attendance_records")
    class_info = relationship("ClassSchedule", back_populates="attendance_records")