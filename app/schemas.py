from pydantic import BaseModel, EmailStr
from datetime import datetime
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