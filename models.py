# models.py
# Описание всех таблиц базы данных через Python-классы (SQLAlchemy ORM)
# Каждый класс = одна таблица в БД
# Каждый Column = один столбец

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum


# ── Перечисления (enum) ──────────────────────────────────────────────────────

class RoleEnum(str, enum.Enum):
    """Роль пользователя в системе"""
    employee = "employee"      # Сотрудник
    manager = "manager"        # Менеджер / Тимлид
    reviewer = "reviewer"      # Проверяющий (принимает/отклоняет задачи)
    boss = "boss"              # Руководитель / Начальник


class TaskStatusEnum(str, enum.Enum):
    """Статус задачи"""
    pending = "pending"            # 🔵 В ожидании выполнения
    in_progress = "in_progress"    # 🟡 В работе
    on_review = "on_review"        # 🟡 На проверке (загружен результат)
    completed = "completed"        # 🟢 Принято / Выполнено
    rejected = "rejected"          # 🔴 Не выполнено / Отклонено


# ── Модели (таблицы) ─────────────────────────────────────────────────────────

class User(Base):
    """Таблица пользователей"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)           # ФИО
    phone = Column(String(20), unique=True, nullable=False)   # Номер телефона
    birth_date = Column(String(10), nullable=False)            # Дата рождения "YYYY-MM-DD"
    hashed_password = Column(String(255), nullable=False)      # Хеш пароля (никогда не храним пароль!)
    position = Column(String(255), nullable=False)             # Должность (свободный текст)
    role = Column(SAEnum(RoleEnum), default=RoleEnum.employee, nullable=False)
    avatar_url = Column(String(500), nullable=True)            # Ссылка на аватар (опционально)
    is_active = Column(Boolean, default=True)
    reset_token = Column(String(64), nullable=True)            # Токен для сброса пароля
    reset_token_expires = Column(DateTime, nullable=True)      # Когда истекает токен
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи (relationships) — SQLAlchemy сам делает JOIN
    org_memberships = relationship("OrgMember", back_populates="user", cascade="all, delete")
    created_tasks = relationship("Task", foreign_keys="Task.creator_id", back_populates="creator")
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    reviewed_tasks = relationship("Task", foreign_keys="Task.reviewer_id", back_populates="reviewer")
    uploaded_files = relationship("TaskFile", back_populates="uploader")


class Organization(Base):
    """Таблица организаций / компаний"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Создатель организации
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("OrgMember", back_populates="org", cascade="all, delete")
    tasks = relationship("Task", back_populates="org", cascade="all, delete")


class OrgMember(Base):
    """Таблица членства в организациях.
    Хранит приглашения (is_accepted=False) и подтверждённых участников (is_accepted=True).
    """
    __tablename__ = "org_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    is_accepted = Column(Boolean, default=False)       # False = приглашение ожидает ответа
    joined_at = Column(DateTime, nullable=True)        # Когда принял приглашение

    user = relationship("User", back_populates="org_memberships")
    org = relationship("Organization", back_populates="members")


class Task(Base):
    """Таблица задач / поручений"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(TaskStatusEnum), default=TaskStatusEnum.pending, nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)    # Кто создал задачу
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)    # Кому назначена
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)    # Кто будет проверять
    deadline = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)   # Комментарий при принятии/отклонении
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org = relationship("Organization", back_populates="tasks")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviewed_tasks")
    attachments = relationship("TaskFile", back_populates="task", cascade="all, delete")


class TaskFile(Base):
    """Таблица файлов, прикреплённых к задачам.
    Хранит как файлы-задания (от создателя), так и файлы-результаты (от исполнителя).
    """
    __tablename__ = "task_files"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=False)     # Оригинальное имя файла
    file_path = Column(String(1000), nullable=False)   # Путь к файлу на сервере
    file_type = Column(String(20), nullable=False)     # "task_file" или "result_file"
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User", back_populates="uploaded_files")