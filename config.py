# config.py
# Читает настройки из файла .env
# pydantic-settings автоматически подхватывает переменные окружения

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа

    # Настройки email
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587

    # База данных
    DATABASE_URL: str = "sqlite:///./taskflow.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаём один экземпляр настроек — импортируем его везде
settings = Settings()