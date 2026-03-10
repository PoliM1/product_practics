# schemas.py
# Pydantic схемы — описывают что именно принимает и возвращает API
# FastAPI автоматически валидирует входящие данные по этим схемам
# и возвращает ошибку 422, если данные не совпадают

from pydantic import BaseModel, EmailStr, field_validator
from models import RoleEnum
from typing import Optional
import re


class UserCreate(BaseModel):
    """Данные для регистрации нового пользователя"""
    email: EmailStr                      # pydantic сам проверяет формат email
    full_name: str
    phone: str
    birth_date: str                      # Формат: "1995-05-20"
    position: str                        # Должность (свободный текст)
    role: RoleEnum = RoleEnum.employee   # По умолчанию — сотрудник
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль должен быть минимум 8 символов")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("ФИО не может быть пустым")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v):
        # Оставляем только цифры и +
        cleaned = re.sub(r"[^\d+]", "", v)
        if len(cleaned) < 10:
            raise ValueError("Некорректный номер телефона")
        return v


class UserLogin(BaseModel):
    """Данные для входа"""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Данные пользователя для ответа API (без пароля!)"""
    id: int
    email: str
    full_name: str
    phone: str
    birth_date: str
    position: str
    role: RoleEnum
    avatar_url: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True  # Позволяет создавать из SQLAlchemy объектов


class PasswordResetRequest(BaseModel):
    """Запрос на сброс пароля — email или телефон"""
    contact: str   # Email или номер телефона


class PasswordReset(BaseModel):
    """Установка нового пароля по токену"""
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль должен быть минимум 8 символов")
        return v


class OrgCreate(BaseModel):
    """Создание организации"""
    name: str
    description: Optional[str] = None


class TaskCreate(BaseModel):
    """Создание задачи (без файлов — файлы идут через Form)"""
    title: str
    description: Optional[str] = None
    org_id: int
    assignee_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    deadline: Optional[str] = None


class StatusUpdate(BaseModel):
    """Обновление статуса задачи"""
    status: str
    comment: Optional[str] = None