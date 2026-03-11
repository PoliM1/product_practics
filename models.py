# models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum


class RoleEnum(str, enum.Enum):
    employee = "employee"
    manager  = "manager"
    reviewer = "reviewer"
    boss     = "boss"


class TaskStatusEnum(str, enum.Enum):
    pending     = "pending"
    in_progress = "in_progress"
    on_review   = "on_review"
    completed   = "completed"
    rejected    = "rejected"


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    full_name        = Column(String(255), nullable=False)
    phone            = Column(String(20),  unique=True, nullable=False)
    birth_date       = Column(String(10),  nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    position         = Column(String(255), nullable=False)
    role             = Column(SAEnum(RoleEnum), default=RoleEnum.employee, nullable=False)
    avatar_url       = Column(String(500), nullable=True)
    is_active        = Column(Boolean, default=True)
    reset_token         = Column(String(64),  nullable=True)
    reset_token_expires = Column(DateTime,    nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    org_memberships = relationship("OrgMember", back_populates="user", cascade="all, delete")
    created_tasks   = relationship("Task", foreign_keys="Task.creator_id",  back_populates="creator")
    assigned_tasks  = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    reviewed_tasks  = relationship("Task", foreign_keys="Task.reviewer_id", back_populates="reviewer")
    uploaded_files  = relationship("TaskFile", back_populates="uploader")


class Organization(Base):
    __tablename__ = "organizations"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text,        nullable=True)
    industry    = Column(String(255), nullable=True)   # Сфера деятельности
    location    = Column(String(255), nullable=True)   # Город / адрес
    website     = Column(String(500), nullable=True)   # Сайт компании
    logo_url    = Column(String(500), nullable=True)   # Ссылка на логотип/фото
    gallery     = Column(Text,        nullable=True)   # JSON список URL фото галереи
    desc_images = Column(Text,        nullable=True)   # Картинки описания (через запятую)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    owner   = relationship("User", foreign_keys=[owner_id])
    members = relationship("OrgMember", back_populates="org", cascade="all, delete")
    tasks   = relationship("Task",      back_populates="org", cascade="all, delete")


class OrgMember(Base):
    __tablename__ = "org_members"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"),         nullable=False)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    is_accepted = Column(Boolean,  default=False)
    joined_at   = Column(DateTime, nullable=True)

    user = relationship("User",         back_populates="org_memberships")
    org  = relationship("Organization", back_populates="members")


class Task(Base):
    __tablename__ = "tasks"

    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String(500), nullable=False)
    description    = Column(Text,        nullable=True)
    status         = Column(SAEnum(TaskStatusEnum), default=TaskStatusEnum.pending, nullable=False)
    org_id         = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id     = Column(Integer, ForeignKey("users.id"),         nullable=False)
    assignee_id    = Column(Integer, ForeignKey("users.id"),         nullable=True)
    reviewer_id    = Column(Integer, ForeignKey("users.id"),         nullable=True)
    deadline       = Column(DateTime, nullable=True)
    review_comment = Column(Text,     nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org         = relationship("Organization", back_populates="tasks")
    creator     = relationship("User", foreign_keys=[creator_id],  back_populates="created_tasks")
    assignee    = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    reviewer    = relationship("User", foreign_keys=[reviewer_id], back_populates="reviewed_tasks")
    attachments = relationship("TaskFile", back_populates="task", cascade="all, delete")


class TaskFile(Base):
    __tablename__ = "task_files"

    id          = Column(Integer, primary_key=True, index=True)
    task_id     = Column(Integer, ForeignKey("tasks.id"),    nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"),    nullable=False)
    filename    = Column(String(500),  nullable=False)
    file_path   = Column(String(1000), nullable=False)
    file_type   = Column(String(20),   nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    task     = relationship("Task", back_populates="attachments")
    uploader = relationship("User", back_populates="uploaded_files")