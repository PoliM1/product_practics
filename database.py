# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Получаем абсолютный путь к папке проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Читаем DATABASE_URL из переменных окружения
# Если не задан — используем SQLite с абсолютным путём
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/taskflow.db")

# Для SQLite нужен параметр check_same_thread=False
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()