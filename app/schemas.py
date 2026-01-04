from pydantic import BaseModel, EmailStr
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

class AttendanceCreate(BaseModel):
    user_uuid: str
    class_id: int
    attendance_date: date

class AttendanceResponse(AttendanceCreate):
    id: int
    class_name: Optional[str] = None # We can populate this in the response
    
    class Config:
        from_attributes = True