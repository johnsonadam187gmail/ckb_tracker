from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from datetime import datetime, date
from typing import Optional, List


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
    current_roles: List[str] = []

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

    @field_validator("end_date")
    @classmethod
    def end_date_after_start_date(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
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
    name: str  # e.g., "Gi", "No-Gi", "Striking"


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
    # teacher_uuid removed - now managed at ClassInstance level


class AttendanceResponse(BaseModel):
    id: int
    attendance_date: date
    user_uuid: str
    class_id: int
    teacher_uuid: Optional[str] = None
    # Add these to get the names in your UI
    user_name: Optional[str] = None
    class_name: Optional[str] = None
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class UserAnalyticsResponse(BaseModel):
    userfullname: str
    id: int
    attendance_date: date
    user_uuid: str
    class_name: str  # From ClassSchedule
    weighting: float  # From ClassSchedule
    rank_at_time: str  # From User
    teacher_uuid: Optional[str] = None
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class ClassAttendanceResponse(BaseModel):
    id: int
    attendance_date: date
    user_uuid: str
    userfullname: str
    rank_at_time: str
    weighting: float
    teacher_uuid: Optional[str] = None
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Role Schemas ---
class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# --- UserRole Schemas ---
class UserRoleAssignment(BaseModel):
    """For assigning roles to a user"""

    role_ids: List[int]


class UserRoleResponse(BaseModel):
    id: int
    user_uuid: str
    role_id: int
    role_name: str
    is_current: bool
    effective_date: datetime
    end_date: Optional[datetime] = None
    created_date: datetime

    class Config:
        from_attributes = True


class UserRoleHistoryResponse(BaseModel):
    user_uuid: str
    user_full_name: str
    current_roles: List[str]
    history: List[UserRoleResponse]

    class Config:
        from_attributes = True


# --- Teacher Analytics Schema ---
class TeacherAnalyticsResponse(BaseModel):
    teacher_uuid: str
    teacher_name: str
    class_name: str
    class_date: date
    student_count: int
    total_weighting: float

    class Config:
        from_attributes = True


# --- Curriculum Schemas ---
class CurriculumBase(BaseModel):
    class_id: int
    name: Optional[str] = None
    description: Optional[str] = None


class CurriculumCreate(CurriculumBase):
    pass


class CurriculumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CurriculumResponse(CurriculumBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Lesson Schemas ---
class LessonBase(BaseModel):
    curriculum_id: int
    title: str
    description: Optional[str] = None
    lesson_plan_url: Optional[HttpUrl] = None
    video_folder_url: Optional[HttpUrl] = None


class LessonCreate(LessonBase):
    pass


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    lesson_plan_url: Optional[HttpUrl] = None
    video_folder_url: Optional[HttpUrl] = None


class LessonResponse(LessonBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- ClassInstance Schemas (Lesson Assignments) ---
class ClassInstanceBase(BaseModel):
    class_id: int
    class_date: date
    teacher_uuid: Optional[str] = None
    lesson_id: Optional[int] = None


class ClassInstanceCreate(ClassInstanceBase):
    pass


class ClassInstanceUpdate(BaseModel):
    teacher_uuid: Optional[str] = None
    lesson_id: Optional[int] = None


class ClassInstanceResponse(ClassInstanceBase):
    id: int
    class_name: Optional[str] = None  # Populated from join
    teacher_name: Optional[str] = None  # Populated from join
    # Lesson details (populated from join with Lesson table)
    lesson_title: Optional[str] = None
    lesson_description: Optional[str] = None
    lesson_plan_url: Optional[str] = None
    video_folder_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
