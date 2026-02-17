from .database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Date,
    Float,
    Text,
    Boolean,
    UniqueConstraint,
    and_,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, foreign
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"

    # Composite unique constraint for SCD Type 2 versioning
    # Only one current version per user_uuid allowed
    __table_args__ = (
        UniqueConstraint("user_uuid", "is_current", name="uix_user_current"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_uuid = Column(String, index=True)  # Removed unique=True for SCD Type 2
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # For Auth
    rank = Column(String(50))
    last_graded_date = Column(Date, nullable=True)

    comments = Column(Text, nullable=True)
    nicknames = Column(Text, nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    # SCD TYPE 2 TRACKING
    is_current = Column(Boolean, default=True)
    effective_date = Column(DateTime, default=datetime.now(timezone.utc))
    end_date = Column(DateTime, nullable=True)

    created_date = Column(DateTime, default=datetime.now(timezone.utc))
    updated_date = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Relationships
    attendance_records = relationship(
        "FactAttendance", back_populates="user", foreign_keys="FactAttendance.user_uuid"
    )
    user_roles = relationship("UserRole", back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_uuid = Column(
        String, ForeignKey("users.user_uuid"), index=True, nullable=False
    )
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # SCD Type 2 Tracking
    is_current = Column(Boolean, default=True, index=True)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_date = Column(DateTime, nullable=True)
    created_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    attendance_records = relationship("FactAttendance", back_populates="user_role")


class ClassSchedule(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    class_uuid = Column(String(50), index=True)  # Anchor for the class
    class_name = Column(String(100), nullable=False)
    day = Column(String(20))
    time = Column(String(20))
    description = Column(Text)
    points = Column(Float, default=1.0)

    gym_id = Column(Integer, ForeignKey("gym_locations.id"))
    class_type_id = Column(Integer, ForeignKey("class_types.id"))

    # SCD Tracking Columns
    is_current = Column(Boolean, default=True, server_default="1")
    effective_date = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    end_date = Column(DateTime, nullable=True)
    created_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    attendance_records = relationship("FactAttendance", back_populates="class_info")
    gym = relationship("GymLocation")
    type = relationship("ClassType")
    curriculum = relationship(
        "Curriculum", uselist=False, back_populates="class_schedule"
    )


class Term(Base):
    __tablename__ = "terms"

    id = Column(Integer, primary_key=True, index=True)
    term_name = Column(String, unique=True, index=True)  # e.g., "Winter Term 2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TermTarget(Base):
    __tablename__ = "term_targets"

    id = Column(Integer, primary_key=True, index=True)
    term_id = Column(Integer, ForeignKey("terms.id"))
    rank = Column(String)  # e.g., "White Belt", "Blue Belt"
    target = Column(Float)  # The "arbitrary number" set by instructor

    term = relationship("Term")


class GymLocation(Base):
    __tablename__ = "gym_locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # e.g., "Downtown HQ"
    address = Column(String)


class ClassType(Base):
    __tablename__ = "class_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class Curriculum(Base):
    """Represents a curriculum for a class (stream).

    Each class has exactly ONE curriculum which contains multiple lessons.
    This is a 1:1 relationship with ClassSchedule.
    """

    __tablename__ = "curricula"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(
        Integer, ForeignKey("classes.id"), unique=True, nullable=False, index=True
    )
    name = Column(String(200))
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    class_schedule = relationship("ClassSchedule", back_populates="curriculum")
    lessons = relationship(
        "Lesson", back_populates="curriculum", cascade="all, delete-orphan"
    )


class Lesson(Base):
    """Represents a lesson template in a curriculum.

    Lessons are reusable content (title, description, URLs) that can be
    assigned to multiple ClassInstances (dates).
    """

    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    curriculum_id = Column(
        Integer, ForeignKey("curricula.id"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    lesson_plan_url = Column(String(500), nullable=True)
    video_folder_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    curriculum = relationship("Curriculum", back_populates="lessons")
    class_instances = relationship("ClassInstance", back_populates="lesson")


class ClassInstance(Base):
    """Represents a specific class instance on a particular date.

    This model captures:
    - A scheduled class (ClassSchedule) happening on a specific date
    - The teacher assigned to teach that class instance
    - The lesson (from curriculum) assigned to this session
    """

    __tablename__ = "class_instances"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    class_date = Column(Date, nullable=False, index=True)
    teacher_uuid = Column(
        String, ForeignKey("users.user_uuid"), nullable=True, index=True
    )
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("class_id", "class_date", name="_class_date_uc"),
    )

    # Relationships
    class_schedule = relationship("ClassSchedule", backref="class_instances")
    teacher = relationship(
        "User",
        foreign_keys=[teacher_uuid],
        primaryjoin="and_(ClassInstance.teacher_uuid == User.user_uuid, User.is_current == True)",
        viewonly=True,
    )
    lesson = relationship("Lesson", back_populates="class_instances")
    attendance_records = relationship("FactAttendance", back_populates="class_instance")


class FactAttendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_uuid = Column(
        String, ForeignKey("users.user_uuid"), index=True, nullable=False
    )
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    class_instance_id = Column(
        Integer, ForeignKey("class_instances.id"), nullable=True, index=True
    )
    teacher_uuid = Column(
        String, ForeignKey("users.user_uuid"), nullable=True, index=True
    )  # Deprecated: use class_instance.teacher_uuid instead
    user_role_id = Column(Integer, ForeignKey("user_roles.id"), nullable=True)

    attendance_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # NEW FIELDS - Mat-side workflow support
    status = Column(String(20), default="confirmed", nullable=False, index=True)
    confirmed_by = Column(
        String, ForeignKey("users.user_uuid"), nullable=True, index=True
    )
    confirmed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_uuid", "class_id", "attendance_date", name="_user_class_date_uc"
        ),
    )

    # Relationships
    user = relationship(
        "User", foreign_keys=[user_uuid], back_populates="attendance_records"
    )
    teacher = relationship("User", foreign_keys=[teacher_uuid])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    class_info = relationship("ClassSchedule", back_populates="attendance_records")
    class_instance = relationship("ClassInstance", back_populates="attendance_records")
    user_role = relationship("UserRole", back_populates="attendance_records")


class ClassFeedback(Base):
    """Represents student feedback for a specific class attendance.

    Students can provide feedback (thumbs up/down + comment) within 7 days
    of attending a class. Feedback is tied to attendance records (one per attendance).
    """

    __tablename__ = "class_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_uuid = Column(
        String, ForeignKey("users.user_uuid"), nullable=False, index=True
    )
    attendance_id = Column(
        Integer, ForeignKey("attendance.id"), nullable=False, index=True
    )
    class_instance_id = Column(
        Integer, ForeignKey("class_instances.id"), nullable=False, index=True
    )

    # Feedback Fields (both optional)
    rating = Column(String(10), nullable=True)  # "thumbs_up", "thumbs_down", or NULL
    comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Constraints: One feedback per attendance record
    __table_args__ = (
        UniqueConstraint("attendance_id", name="_attendance_feedback_uc"),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_uuid])
    attendance = relationship("FactAttendance", backref="feedback")
    class_instance = relationship("ClassInstance", backref="feedback_records")
