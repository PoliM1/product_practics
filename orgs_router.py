# routers/orgs_router.py
import os, uuid, json, aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Organization, OrgMember, User
from auth import get_current_user
from schemas import OrgCreate
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/orgs", tags=["Организации"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

class OrgUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None

async def save_image(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="Разрешены только JPG, PNG, WEBP, GIF")
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Максимум 5MB")
        await f.write(content)
    return f"/orgs/image/{unique_name}"

@router.post("/create")
def create_org(data: OrgCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = Organization(name=data.name, description=data.description, owner_id=current_user.id)
    db.add(org)
    db.flush()
    db.add(OrgMember(user_id=current_user.id, org_id=org.id, is_accepted=True, joined_at=datetime.utcnow()))
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name, "message": "Организация создана!"}

@router.get("/my-orgs")
def get_my_orgs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memberships = db.query(OrgMember).filter(OrgMember.user_id == current_user.id, OrgMember.is_accepted == True).all()
    return [{"id": m.org.id, "name": m.org.name, "description": m.org.description,
             "owner": m.org.owner.full_name, "owner_id": m.org.owner_id,
             "is_owner": m.org.owner_id == current_user.id,
             "members_count": db.query(OrgMember).filter(OrgMember.org_id == m.org.id, OrgMember.is_accepted == True).count()}
            for m in memberships]

@router.get("/my-invitations")
def get_invitations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invitations = db.query(OrgMember).filter(OrgMember.user_id == current_user.id, OrgMember.is_accepted == False).all()
    return [{"id": inv.id, "org_id": inv.org.id, "org_name": inv.org.name,
             "org_description": inv.org.description, "owner_name": inv.org.owner.full_name}
            for inv in invitations]

@router.get("/image/{filename}")
def get_image(filename: str):
    filename = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Изображение не найдено")
    ext = os.path.splitext(filename)[1].lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    return FileResponse(file_path, media_type=media_types.get(ext, "image/jpeg"))

@router.get("/{org_id}/info")
def get_org_info(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    membership = db.query(OrgMember).filter(OrgMember.user_id == current_user.id, OrgMember.org_id == org_id, OrgMember.is_accepted == True).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Нет доступа")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Организация не найдена")
    gallery_raw = getattr(org, 'gallery', None)
    gallery = []
    if gallery_raw:
        try: gallery = json.loads(gallery_raw)
        except: gallery = []
    return {"id": org.id, "name": org.name, "description": org.description,
            "industry": getattr(org, 'industry', None), "location": getattr(org, 'location', None),
            "website": getattr(org, 'website', None), "logo_url": getattr(org, 'logo_url', None),
            "gallery": gallery, "owner_id": org.owner_id, "owner_name": org.owner.full_name,
            "created_at": str(org.created_at)}

@router.patch("/{org_id}/update")
def update_org(org_id: int, data: OrgUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org: raise HTTPException(status_code=404, detail="Не найдена")
    if org.owner_id != current_user.id: raise HTTPException(status_code=403, detail="Только руководитель")
    org.name = data.name
    org.description = data.description
    for field in ['industry', 'location', 'website']:
        if hasattr(org, field): setattr(org, field, getattr(data, field))
    if hasattr(org, 'logo_url') and data.logo_url is not None:
        org.logo_url = data.logo_url
    db.commit()
    return {"message": "Сохранено"}

@router.post("/{org_id}/upload-logo")
async def upload_logo(org_id: int, file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org: raise HTTPException(status_code=404, detail="Не найдена")
    if org.owner_id != current_user.id: raise HTTPException(status_code=403, detail="Только руководитель")
    url = await save_image(file)
    if hasattr(org, 'logo_url'):
        org.logo_url = url
        db.commit()
    return {"logo_url": url, "message": "Логотип обновлён!"}

@router.post("/{org_id}/upload-gallery")
async def upload_gallery_image(org_id: int, file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org: raise HTTPException(status_code=404, detail="Не найдена")
    if org.owner_id != current_user.id: raise HTTPException(status_code=403, detail="Только руководитель")
    url = await save_image(file)
    current_gallery = []
    if hasattr(org, 'gallery') and org.gallery:
        try: current_gallery = json.loads(org.gallery)
        except: current_gallery = []
    current_gallery.append(url)
    if hasattr(org, 'gallery'):
        org.gallery = json.dumps(current_gallery)
        db.commit()
    return {"url": url, "gallery": current_gallery, "message": "Фото добавлено!"}

@router.delete("/{org_id}/gallery")
async def delete_gallery_image(org_id: int, url: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org or org.owner_id != current_user.id: raise HTTPException(status_code=403, detail="Нет доступа")
    current_gallery = []
    if hasattr(org, 'gallery') and org.gallery:
        try: current_gallery = json.loads(org.gallery)
        except: current_gallery = []
    current_gallery = [u for u in current_gallery if u != url]
    if hasattr(org, 'gallery'):
        org.gallery = json.dumps(current_gallery)
        db.commit()
    return {"gallery": current_gallery}

@router.post("/{org_id}/leave")
def leave_org(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org: raise HTTPException(status_code=404, detail="Не найдена")
    if org.owner_id == current_user.id: raise HTTPException(status_code=400, detail="Владелец не может покинуть организацию")
    membership = db.query(OrgMember).filter(OrgMember.user_id == current_user.id, OrgMember.org_id == org_id).first()
    if not membership: raise HTTPException(status_code=404, detail="Вы не в этой организации")
    db.delete(membership)
    db.commit()
    return {"message": f"Вы покинули организацию «{org.name}»"}

@router.post("/{org_id}/invite/{user_id}")
def invite_user(org_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org or org.owner_id != current_user.id: raise HTTPException(status_code=403, detail="Только владелец")
    target = db.query(User).filter(User.id == user_id).first()
    if not target: raise HTTPException(status_code=404, detail="Пользователь не найден")
    existing = db.query(OrgMember).filter(OrgMember.user_id == user_id, OrgMember.org_id == org_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже состоит или приглашён")
    db.add(OrgMember(user_id=user_id, org_id=org_id, is_accepted=False))
    db.commit()
    return {"message": f"Приглашение отправлено {target.full_name}"}

@router.post("/invitations/{invitation_id}/accept")
def accept_invitation(invitation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(OrgMember).filter(OrgMember.id == invitation_id, OrgMember.user_id == current_user.id).first()
    if not inv: raise HTTPException(status_code=404, detail="Не найдено")
    inv.is_accepted = True
    inv.joined_at = datetime.utcnow()
    db.commit()
    return {"message": f"Вы вступили в «{inv.org.name}»!"}

@router.post("/invitations/{invitation_id}/decline")
def decline_invitation(invitation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(OrgMember).filter(OrgMember.id == invitation_id, OrgMember.user_id == current_user.id).first()
    if not inv: raise HTTPException(status_code=404, detail="Не найдено")
    db.delete(inv)
    db.commit()
    return {"message": "Отклонено"}

@router.get("/{org_id}/members")
def get_members(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    membership = db.query(OrgMember).filter(OrgMember.user_id == current_user.id, OrgMember.org_id == org_id, OrgMember.is_accepted == True).first()
    if not membership: raise HTTPException(status_code=403, detail="Нет доступа")
    members = db.query(OrgMember).filter(OrgMember.org_id == org_id, OrgMember.is_accepted == True).all()
    return [{"id": m.user.id, "full_name": m.user.full_name, "email": m.user.email,
             "position": m.user.position, "role": m.user.role,
             "joined_at": str(m.joined_at) if m.joined_at else None} for m in members]