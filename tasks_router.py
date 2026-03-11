# routers/tasks_router.py
# Управление задачами и файлами:
# POST   /tasks/create                   — создать задачу (с файлами)
# GET    /tasks/org/{org_id}             — все задачи организации
# GET    /tasks/my                       — мои задачи (назначены мне)
# PATCH  /tasks/{id}/status             — изменить статус
# POST   /tasks/{id}/upload-result      — загрузить результат работы
# GET    /tasks/file/{file_id}/download — скачать файл

import os
import uuid
from typing import Optional, List
from datetime import datetime

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Task, TaskFile, OrgMember, TaskStatusEnum, User
from auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Задачи"])

# Папка для хранения файлов
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Разрешённые типы файлов
ALLOWED_EXTENSIONS = {
    ".docx", ".doc",     # Word
    ".xlsx", ".xls",     # Excel
    ".pdf",              # PDF
    ".txt",              # Блокнот
    ".accdb", ".mdb",    # Access
}

# Соответствие расширений MIME-типам (для скачивания)
MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".accdb": "application/msaccess",
    ".mdb": "application/msaccess",
}


def check_org_membership(user_id: int, org_id: int, db: Session) -> bool:
    """Проверяет что пользователь состоит в организации."""
    return db.query(OrgMember).filter(
        OrgMember.user_id == user_id,
        OrgMember.org_id == org_id,
        OrgMember.is_accepted == True,
    ).first() is not None


def task_to_dict(task: Task) -> dict:
    """Сериализует задачу в словарь для JSON ответа."""
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "deadline": task.deadline.strftime("%Y-%m-%d %H:%M") if task.deadline else None,
        "review_comment": task.review_comment,
        "created_at": str(task.created_at),
        "creator": {"id": task.creator_id, "name": task.creator.full_name if task.creator else "?"},
        "assignee": {"id": task.assignee_id, "name": task.assignee.full_name if task.assignee else None},
        "reviewer": {"id": task.reviewer_id, "name": task.reviewer.full_name if task.reviewer else None},
        "files": [
            {
                "id": f.id,
                "name": f.filename,
                "type": f.file_type,   # "task_file" или "result_file"
                "uploaded_by": f.uploader.full_name if f.uploader else "?",
                "uploaded_at": str(f.uploaded_at),
            }
            for f in task.attachments
        ],
    }


@router.post("/create", summary="Создать задачу")
async def create_task(
    title: str = Form(...),
    description: str = Form(""),
    org_id: int = Form(...),
    assignee_id: Optional[int] = Form(None),
    reviewer_id: Optional[int] = Form(None),
    deadline: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создаёт задачу с возможностью прикрепить файлы (Word, Excel, PDF, TXT, Access)."""

    if not check_org_membership(current_user.id, org_id, db):
        raise HTTPException(status_code=403, detail="Вы не состоите в этой организации")

    task = Task(
        title=title,
        description=description,
        org_id=org_id,
        creator_id=current_user.id,
        assignee_id=assignee_id,
        reviewer_id=reviewer_id,
        deadline=datetime.fromisoformat(deadline) if deadline else None,
    )
    db.add(task)
    db.flush()  # Получаем task.id

    # Сохраняем прикреплённые файлы
    saved_files = []
    for file in files:
        if not file.filename:
            continue
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue  # Пропускаем недопустимые форматы

        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        task_file = TaskFile(
            task_id=task.id,
            uploader_id=current_user.id,
            filename=file.filename,
            file_path=file_path,
            file_type="task_file",
        )
        db.add(task_file)
        saved_files.append(file.filename)

    db.commit()
    return {"id": task.id, "message": "Задача создана", "files_attached": saved_files}


@router.get("/org/{org_id}", summary="Все задачи организации")
def get_org_tasks(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает все задачи организации. Видны всем участникам."""

    if not check_org_membership(current_user.id, org_id, db):
        raise HTTPException(status_code=403, detail="У вас нет доступа к этой организации")

    tasks = db.query(Task).filter(Task.org_id == org_id).order_by(Task.created_at.desc()).all()
    return [task_to_dict(t) for t in tasks]


@router.get("/my", summary="Задачи назначенные мне")
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает задачи где текущий пользователь — исполнитель или проверяющий."""
    tasks = db.query(Task).filter(
        (Task.assignee_id == current_user.id) | (Task.reviewer_id == current_user.id)
    ).order_by(Task.created_at.desc()).all()
    return [task_to_dict(t) for t in tasks]


@router.get("/{task_id}", summary="Одна задача")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if not check_org_membership(current_user.id, task.org_id, db):
        raise HTTPException(status_code=403, detail="Нет доступа")
    return task_to_dict(task)


@router.patch("/{task_id}/status", summary="Изменить статус задачи")
def update_status(
    task_id: int,
    status: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Изменяет статус задачи с проверкой прав."""

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Проверяем что пользователь состоит в организации
    if not check_org_membership(current_user.id, task.org_id, db):
        raise HTTPException(status_code=403, detail="Нет доступа")

    # Проверяем допустимые значения статуса
    valid_statuses = [s.value for s in TaskStatusEnum]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Статус должен быть одним из: {valid_statuses}")

    # Принять/отклонить может только проверяющий или создатель
    if status in ("completed", "rejected"):
        can_review = (
            task.reviewer_id == current_user.id
            or task.creator_id == current_user.id
        )
        if not can_review:
            raise HTTPException(status_code=403, detail="Только проверяющий или создатель может принять/отклонить задачу")

    # Взять в работу может только исполнитель
    if status == "in_progress" and task.assignee_id:
        if task.assignee_id != current_user.id:
            raise HTTPException(status_code=403, detail="Только назначенный исполнитель может взять задачу в работу")

    task.status = status
    if comment:
        task.review_comment = comment
    task.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Статус обновлён", "new_status": status}


@router.post("/{task_id}/upload-result", summary="Загрузить результат работы")
async def upload_result(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Исполнитель загружает готовую работу. Статус автоматически становится 'На проверке'."""

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Загрузить результат может исполнитель или любой участник организации
    if not check_org_membership(current_user.id, task.org_id, db):
        raise HTTPException(status_code=403, detail="Нет доступа")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    task_file = TaskFile(
        task_id=task.id,
        uploader_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_type="result_file",
    )
    db.add(task_file)

    # Автоматически переводим задачу на проверку
    task.status = TaskStatusEnum.on_review
    task.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Результат загружен. Задача отправлена на проверку."}


@router.get("/file/{file_id}/download", summary="Скачать файл")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Скачивает файл прикреплённый к задаче."""

    task_file = db.query(TaskFile).filter(TaskFile.id == file_id).first()
    if not task_file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    # Проверяем доступ через организацию
    if not check_org_membership(current_user.id, task_file.task.org_id, db):
        raise HTTPException(status_code=403, detail="Нет доступа к этому файлу")

    if not os.path.exists(task_file.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")

    ext = os.path.splitext(task_file.filename)[1].lower()
    media_type = MIME_TYPES.get(ext, "application/octet-stream")

    return FileResponse(
        path=task_file.file_path,
        filename=task_file.filename,
        media_type=media_type,
    )