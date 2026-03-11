# routers/auth_router.py
# Все эндпоинты связанные с аутентификацией:
# POST /auth/register      — регистрация
# POST /auth/login         — вход
# GET  /auth/me            — данные текущего пользователя
# POST /auth/forgot-password — запрос сброса пароля
# POST /auth/reset-password  — установка нового пароля

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import hash_password, verify_password, create_access_token, get_current_user
from schemas import UserCreate, UserLogin, PasswordResetRequest, PasswordReset
import secrets
import string
from datetime import datetime, timedelta
from config import settings

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


# ── Вспомогательная функция отправки email ───────────────────────────────────

async def send_reset_email(email: str, reset_link: str):
    """Отправляет письмо со ссылкой сброса пароля.
    Если почта не настроена — просто печатает в консоль (для разработки).
    Использует встроенный smtplib — работает на Python 3.14 без доп. библиотек.
    """
    if not settings.MAIL_USERNAME:
        # Режим разработки — показываем ссылку прямо в консоли терминала
        print(f"\n{'='*55}")
        print(f"  СБРОС ПАРОЛЯ (dev-режим, email не настроен)")
        print(f"  Для кого: {email}")
        print(f"  Ссылка:   {reset_link}")
        print(f"{'='*55}\n")
        return

    # Используем встроенный smtplib — не нужно ничего устанавливать
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
            <h2 style="color: #7C3AED;">✅ TaskFlow — Сброс пароля</h2>
            <p>Вы запросили сброс пароля. Нажмите на кнопку ниже:</p>
            <a href="{reset_link}"
               style="display:inline-block; padding:12px 24px; background:#7C3AED;
                      color:white; text-decoration:none; border-radius:8px; font-weight:bold;">
               Сбросить пароль
            </a>
            <p style="color:#6B7280; font-size:13px; margin-top:16px;">
                Ссылка действительна 1 час.<br>
                Если вы не запрашивали сброс — проигнорируйте это письмо.
            </p>
        </div>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Восстановление пароля TaskFlow"
        msg["From"]    = settings.MAIL_FROM
        msg["To"]      = email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Подключаемся к Gmail через STARTTLS
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_FROM, email, msg.as_string())

        print(f"✅ Письмо отправлено на {email}")

    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")
        # Показываем ссылку в консоли как запасной вариант
        print(f"   Ссылка для сброса: {reset_link}")


# ── Эндпоинты ────────────────────────────────────────────────────────────────

@router.post("/register", summary="Регистрация нового пользователя")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Регистрирует нового пользователя. Возвращает JWT токен."""

    # Проверяем уникальность email
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    # Проверяем уникальность телефона
    if db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(status_code=400, detail="Номер телефона уже используется")

    # Создаём пользователя (пароль хешируем!)
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        phone=user_data.phone,
        birth_date=user_data.birth_date,
        position=user_data.position,
        role=user_data.role,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name,
    }


@router.post("/login", summary="Вход в систему")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Проверяет email и пароль, возвращает JWT токен."""

    user = db.query(User).filter(User.email == credentials.email).first()

    # Проверяем и пользователя и пароль одновременно (защита от timing attack)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role,
    }


@router.get("/me", summary="Данные текущего пользователя")
def get_me(current_user: User = Depends(get_current_user)):
    """Возвращает данные авторизованного пользователя."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "birth_date": current_user.birth_date,
        "position": current_user.position,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "created_at": str(current_user.created_at),
    }


@router.post("/forgot-password", summary="Запрос сброса пароля")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Отправляет письмо со ссылкой сброса пароля на email пользователя."""

    # Ищем по email ИЛИ по телефону
    user = db.query(User).filter(
        (User.email == request.contact) | (User.phone == request.contact)
    ).first()

    # Возвращаем одинаковый ответ независимо от результата
    # (чтобы нельзя было узнать зарегистрирован ли email)
    if not user:
        return {"message": "Если аккаунт найден — инструкции отправлены"}

    # Генерируем безопасный случайный токен
    token = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    # Ссылка для сброса (замени домен при деплое)
    reset_link = f"{settings.APP_URL if hasattr(settings, 'APP_URL') else 'http://localhost:8000'}/reset-password?token={token}"

    # Отправляем email в фоне (не блокирует ответ API)
    background_tasks.add_task(send_reset_email, user.email, reset_link)

    return {"message": "Если аккаунт найден — инструкции отправлены"}


@router.post("/reset-password", summary="Установка нового пароля")
async def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    """Устанавливает новый пароль по токену из письма."""

    user = db.query(User).filter(User.reset_token == data.token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Неверный токен сброса пароля")

    if user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Токен истёк. Запросите сброс повторно.")

    # Устанавливаем новый пароль
    user.hashed_password = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Пароль успешно изменён. Теперь можно войти."}