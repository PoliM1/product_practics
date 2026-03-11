# routers/users_router.py
# Эндпоинты профиля пользователя:
# GET  /users/profile          — просмотр своего профиля
# GET  /users/search?q=...     — поиск пользователей (для приглашений)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import get_current_user

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get("/profile", summary="Профиль текущего пользователя")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Возвращает полный профиль со списком организаций."""
    from models import OrgMember

    # Получаем все принятые членства
    memberships = db.query(OrgMember).filter(
        OrgMember.user_id == current_user.id,
        OrgMember.is_accepted == True,
    ).all()

    orgs = [
        {
            "id": m.org.id,
            "name": m.org.name,
            "description": m.org.description,
            "owner": m.org.owner.full_name,
            "is_owner": m.org.owner_id == current_user.id,
        }
        for m in memberships
    ]

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
        "organizations": orgs,
    }


@router.get("/search", summary="Поиск пользователей по email или имени")
def search_users(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ищет пользователей по email или имени. Используется для приглашений в организацию."""
    search = f"%{q}%"
    users = db.query(User).filter(
        (User.email.ilike(search)) | (User.full_name.ilike(search))
    ).filter(User.id != current_user.id).limit(10).all()

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "position": u.position,
            "role": u.role,
        }
        for u in users
    ]