
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from config import settings

# CryptContext настраивает алгоритм хеширования
# bcrypt — золотой стандарт для паролей, очень медленный по задумке
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTPBearer извлекает токен из заголовка Authorization: Bearer <token>
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Превращает пароль '12345678' в хеш '$2b$12$...' """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет что пароль соответствует хешу. Возвращает True/False."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Создаёт JWT токен.
    
    JWT = JSON Web Token.
    Структура: header.payload.signature
    Payload содержит: user_id, email, время истечения.
    Подписан SECRET_KEY — сервер может проверить подпись без БД.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Расшифровывает JWT токен. Возвращает payload или None если токен невалидный."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """FastAPI зависимость — получает текущего пользователя из JWT токена.
    
    Использование в роутере:
        @router.get("/profile")
        def my_profile(current_user = Depends(get_current_user)):
            return current_user.full_name
    """
    from models import User  # импорт здесь чтобы избежать циклического импорта

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен недействителен или истёк. Войдите снова.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Некорректный токен")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт деактивирован")

    return user