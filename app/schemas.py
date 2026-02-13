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
    points: float = 1.0


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
    points: Optional[float] = None


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
    # Mat-side workflow fields
    status: str = "confirmed"  # "pending" or "confirmed"
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    confirmer_name: Optional[str] = None
    # Additional user details for dashboard
    profile_image_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    rank: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserAnalyticsResponse(BaseModel):
    userfullname: str
    id: int
    attendance_date: date
    user_uuid: str
    class_name: str  # From ClassSchedule
    points: float  # From ClassSchedule
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
    points: float
    teacher_uuid: Optional[str] = None
    teacher_name: Optional[str] = None
    status: str = "confirmed"

    class Config:
        from_attributes = True


# --- Mat-Side Workflow Schemas ---
class StudentCheckInRequest(BaseModel):
    """Schema for student self check-in."""

    user_uuid: str
    class_id: int
    attendance_date: date


class PendingAttendanceResponse(BaseModel):
    """Schema for pending attendance records (teacher view)."""

    id: int
    user_uuid: str
    student_name: str
    class_id: int
    class_name: str
    attendance_date: date
    created_at: datetime
    profile_image_url: Optional[str] = None
    status: str = "pending"

    class Config:
        from_attributes = True


class BulkConfirmRequest(BaseModel):
    """Schema for bulk confirming attendance records."""

    attendance_ids: List[int]


class DirectAttendanceRequest(BaseModel):
    """Schema for teacher direct attendance (bypasses self check-in)."""

    user_uuid: str
    class_id: int
    attendance_date: date


# --- User Search Schema ---
class UserSearchResponse(BaseModel):
    """Schema for user search results (minimal info for disambiguation)."""

    user_uuid: str
    first_name: str
    last_name: str
    email: str
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True


# --- Kiosk Schemas ---
class KioskPinVerifyRequest(BaseModel):
    """Schema for kiosk PIN verification."""

    pin: str


class KioskPinVerifyResponse(BaseModel):
    """Schema for kiosk PIN verification response."""

    message: str
    valid: bool


class KioskPinUpdateRequest(BaseModel):
    """Schema for updating kiosk PIN (admin only)."""

    current_pin: str
    new_pin: str

    @field_validator("new_pin")
    @classmethod
    def validate_pin(cls, v):
        """Validate PIN is 4-6 digits."""
        if not v.isdigit():
            raise ValueError("PIN must contain only numbers")
        if len(v) < 4 or len(v) > 6:
            raise ValueError("PIN must be 4-6 digits")
        return v


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
    total_points: float

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


# --- Feedback Schemas ---
class FeedbackCreate(BaseModel):
    """Schema for creating or updating feedback."""

    attendance_id: int
    rating: Optional[str] = None  # "thumbs_up", "thumbs_down", or None
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        """Validate rating is one of the allowed values."""
        if v and v not in ["thumbs_up", "thumbs_down"]:
            raise ValueError('Rating must be "thumbs_up" or "thumbs_down"')
        return v

    class Config:
        from_attributes = True


class FeedbackUpdate(BaseModel):
    """Schema for updating existing feedback."""

    rating: Optional[str] = None
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        """Validate rating is one of the allowed values."""
        if v and v not in ["thumbs_up", "thumbs_down"]:
            raise ValueError('Rating must be "thumbs_up" or "thumbs_down"')
        return v

    class Config:
        from_attributes = True


class FeedbackResponse(BaseModel):
    """Schema for feedback responses with joined data."""

    id: int
    user_uuid: str
    attendance_id: int
    class_instance_id: int
    rating: Optional[str]
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Joined fields from related tables
    user_full_name: Optional[str] = None
    class_name: Optional[str] = None
    class_date: Optional[date] = None
    lesson_title: Optional[str] = None
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class FeedbackStatsResponse(BaseModel):
    """Schema for aggregated feedback statistics."""

    class_instance_id: int
    class_name: str
    class_date: date
    teacher_name: Optional[str] = None
    thumbs_up_count: int
    thumbs_down_count: int
    total_feedback: int
    total_attendees: int
    feedback_rate: float  # Percentage of attendees who left feedback

    class Config:
        from_attributes = True


# ===== Authentication Schemas =====
class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str

    class Config:
        from_attributes = True


class SetPasswordRequest(BaseModel):
    """Schema for setting/updating user password."""

    user_uuid: str
    password: str

    class Config:
        from_attributes = True


# ===== Teacher Authentication Schemas =====
class TeacherLoginResponse(BaseModel):
    """Response schema for teacher login with JWT token."""

    access_token: str
    token_type: str
    user_info: "UserResponse"

    class Config:
        from_attributes = True


class SessionVerifyRequest(BaseModel):
    """Request schema for session verification."""

    token: str


class SessionVerifyResponse(BaseModel):
    """Response schema for session verification with new token."""

    status: str
    new_token: str
    user_uuid: str

    class Config:
        from_attributes = True


# ===== Admin Feedback Analytics Schema =====
class ComprehensiveFeedbackStats(BaseModel):
    """Schema for comprehensive feedback with all details (admin view)."""

    rating: Optional[str]
    comment: Optional[str]
    class_date: date
    class_name: str
    student_name: str
    teacher_name: Optional[str]

    class Config:
        from_attributes = True


# ===== Photo Management Schema =====
class UserPhotoResponse(BaseModel):
    """Response schema for photo upload/update operations."""

    message: str
    user_uuid: str
    photo_url: Optional[str]
    thumbnail_url: Optional[str]

    class Config:
        from_attributes = True
