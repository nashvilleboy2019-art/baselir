import json
from datetime import datetime, date
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy.orm import Session
from app import models


# --- Auth helpers ---

def require_login(request: Request, db: Session) -> models.User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401)
    return user


def require_responsable(request: Request, db: Session) -> models.User:
    user = require_login(request, db)
    if user.role != "responsable":
        raise HTTPException(status_code=403, detail="Accès réservé au responsable.")
    return user


# --- App config ---

def get_config(db: Session, key: str, default: str = "") -> str:
    item = db.query(models.AppConfig).filter(models.AppConfig.key == key).first()
    return item.value if item and item.value is not None else default


def set_config(db: Session, key: str, value: str):
    item = db.query(models.AppConfig).filter(models.AppConfig.key == key).first()
    if item:
        item.value = value
    else:
        db.add(models.AppConfig(key=key, value=value))


# --- Activity / history ---

def log_activity(db: Session, user: models.User, action: str,
                 resource: str = None, resource_id=None, details: str = None):
    db.add(models.ActivityLog(
        user_id=user.id,
        username=user.username,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details,
        timestamp=datetime.utcnow(),
    ))


def log_history(db: Session, habilitation_id: int, action: str, user_id: int,
                old_values: dict = None, new_values: dict = None, note: str = None):
    db.add(models.HabilitationHistory(
        habilitation_id=habilitation_id,
        action=action,
        changed_by=user_id,
        old_values=json.dumps(old_values, ensure_ascii=False, default=str) if old_values else None,
        new_values=json.dumps(new_values, ensure_ascii=False, default=str) if new_values else None,
        note=note,
        changed_at=datetime.utcnow(),
    ))


def habilitation_to_dict(h: models.Habilitation, custom_fields=None) -> dict:
    d = {
        "nom_prenom": h.nom_prenom,
        "statut": h.statut.label if h.statut else None,
        "filiale": h.filiale.label if h.filiale else None,
        "description": h.description.label if h.description else None,
        "service": h.service.label if h.service else None,
        "societe": h.societe.label if h.societe else None,
        "role": h.role.label if h.role else None,
        "domaine": h.domaine.label if h.domaine else None,
        "date_octroi": str(h.date_octroi) if h.date_octroi else None,
        "date_attestation": str(h.date_attestation) if h.date_attestation else None,
        "date_sensibilisation": str(h.date_sensibilisation) if h.date_sensibilisation else None,
    }
    if custom_fields:
        for cf in custom_fields:
            key = f"[{cf.custom_type.label}]"
            d[key] = cf.custom_value.label if cf.custom_value else None
    return d


def get_custom_field_map(db: Session, habilitation_id: int) -> dict:
    """Returns {type_id: value_id} for an habilitation."""
    rows = (db.query(models.HabilitationCustomField)
            .filter(models.HabilitationCustomField.habilitation_id == habilitation_id)
            .all())
    return {r.custom_type_id: r.custom_value_id for r in rows}


def save_custom_fields(db: Session, habilitation_id: int, type_value_map: dict):
    """type_value_map = {type_id: value_id or None}"""
    (db.query(models.HabilitationCustomField)
     .filter(models.HabilitationCustomField.habilitation_id == habilitation_id)
     .delete())
    for type_id, value_id in type_value_map.items():
        if value_id:
            db.add(models.HabilitationCustomField(
                habilitation_id=habilitation_id,
                custom_type_id=type_id,
                custom_value_id=value_id,
            ))


# --- Flash ---

def set_flash(request: Request, message: str, category: str = "success"):
    request.session["flash"] = {"message": message, "category": category}


def get_flash(request: Request):
    if "flash" in request.session:
        flash = request.session.pop("flash")
        return flash
    return None


# --- Pagination ---

def paginate(query, page: int, per_page: int = 50) -> dict:
    total = query.count()
    page = max(1, page)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "results": items,
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
        "start": (page - 1) * per_page + 1 if total > 0 else 0,
        "end": min(page * per_page, total),
    }
