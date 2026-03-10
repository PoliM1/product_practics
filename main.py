# main.py
# Точка входа всего приложения.
# Здесь создаётся FastAPI приложение, подключаются все роутеры,
# статические файлы и HTML-шаблоны.

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os

# Импортируем модели ДО create_all, чтобы SQLAlchemy знал о всех таблицах
from database import engine
import models

# Создаём все таблицы в БД (если ещё не созданы)
# В продакшене обычно используют Alembic migrations — но для студентов это проще
models.Base.metadata.create_all(bind=engine)

# Создаём папку для загрузок
os.makedirs("uploads", exist_ok=True)

# ── Создание приложения ──────────────────────────────────────────────────────

app = FastAPI(
    title="TaskFlow",
    description="Корпоративный менеджер задач",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI — интерактивная документация API
    redoc_url="/redoc",     # ReDoc — альтернативная документация
)

# ── CORS middleware ──────────────────────────────────────────────────────────
# CORS позволяет браузеру делать запросы к API с другого домена
# В разработке разрешаем всё, в продакшене — только свой домен
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Заменить на ["https://твой-домен.railway.app"] в продакшене
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Статические файлы и шаблоны ──────────────────────────────────────────────
# StaticFiles отдаёт CSS, JS, изображения по пути /static/...
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Подключаем роутеры ───────────────────────────────────────────────────────
from routers import auth_router, users_router, orgs_router, tasks_router

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(orgs_router.router)
app.include_router(tasks_router.router)

# ── HTML страницы ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    """Страница входа / регистрации"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request):
    """Главная страница с задачами"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/profile", response_class=HTMLResponse, include_in_schema=False)
def profile(request: Request):
    """Страница профиля"""
    return templates.TemplateResponse("profile.html", {"request": request})


@app.get("/reset-password", response_class=HTMLResponse, include_in_schema=False)
def reset_password_page(request: Request):
    """Страница установки нового пароля (по ссылке из письма)"""
    return templates.TemplateResponse("reset_password.html", {"request": request})


@app.get("/health", include_in_schema=False)
def health_check():
    """Railway использует этот эндпоинт для проверки что сервер жив"""
    return {"status": "ok"}


# ── Точка запуска ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # reload=True — автоматически перезапускает сервер при изменении файлов
    # Только для разработки! В продакшене убрать.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)