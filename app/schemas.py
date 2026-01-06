from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, date
from typing import Optional

# What we require when creating a user
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    rank: Optional[str] = None
    comments: Optional[str] = None
    nicknames: Optional[str] = None
    last_graded_date: Optional[datetime] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True

# What we send back to the UI (hiding the password)
class UserResponse(BaseModel):
    id: int
    user_uuid: str
    first_name: str
    last_name: str
    email: str
    rank: Optional[str]
    comments: Optional[str] = None
    nicknames: Optional[str] = None
    last_graded_date: Optional[datetime] = None
    profile_image_url: Optional[str] = None
    created_date: datetime
    is_current: Optional[bool] = False
    effective_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class ClassBase(BaseModel):
    class_name: str
    day: str
    time: str
    description: Optional[str] = None
    weighting: float = 1.0

class ClassCreate(ClassBase):
    pass

class ClassResponse(ClassBase):
    class_name:str
    day: str
    time: str   
    description: Optional[str]
    weighting: float    
    id: int
    class_uuid: str
    is_current: bool
    effective_date: datetime
    
    class Config:
        from_attributes = True

class ClassUpdate(BaseModel):
    class_name: Optional[str] = None
    day: Optional[str] = None
    time: Optional[str] = None
    description: Optional[str] = None
    weighting: Optional[float] = None

class TermBase(BaseModel):
    term_name: str
    start_date: date
    end_date: date

    @field_validator('end_date')
    @classmethod
    def end_date_after_start_date(cls, v, info):
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

class TermCreate(TermBase):
    pass

class TermUpdate(BaseModel):
    term_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class TermResponse(TermBase):
    id: int
    class Config:
        from_attributes = True

class TermTargetBase(BaseModel):
    term_id: int
    rank: str
    target: float  # Renamed from target_hours

class TermTargetCreate(TermTargetBase):
    pass

class TermTargetResponse(TermTargetBase):
    id: int
    class Config:
        from_attributes = True

class TermTargetUpdate(BaseModel):
    target: float  # For changing the performance number

# --- Gym Location Schemas ---
class GymBase(BaseModel):
    name: str
    address: Optional[str] = None

class GymCreate(GymBase):
    pass

class GymResponse(GymBase):
    id: int
    class Config:
        from_attributes = True

# --- Class Type Schemas ---
class ClassTypeBase(BaseModel):
    name: str # e.g., "Gi", "No-Gi", "Striking"

class ClassTypeCreate(ClassTypeBase):
    pass

class ClassTypeResponse(ClassTypeBase):
    id: int
    class Config:
        from_attributes = True
# --- Attendance Schemas ---
class AttendanceCreate(BaseModel):
    user_uuid: str
    class_id: int
    attendance_date: date

class AttendanceResponse(BaseModel):
    id: int
    attendance_date: date
    user_uuid: str
    class_id: int
    # Add these to get the names in your UI
    user_name: Optional[str] = None 
    class_name: Optional[str] = None

    class Config:
        from_attributes = True

class UserAnalyticsResponse(BaseModel):
    userfullname: str
    id: int
    attendance_date: date
    user_uuid: str
    class_name: str        # From ClassSchedule
    weighting: float       # From ClassSchedule
    rank_at_time: str      # From User
    
    class Config:
        from_attributes = True

class ClassAttendanceResponse(BaseModel):
    id: int
    attendance_date: date
    user_uuid: str
    userfullname: str
    rank_at_time: str
    weighting: float 

    class Config:
        from_attributes = True