import hashlib
import secrets
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter()

_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=True)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_hash, key_prefix)."""
    raw = "lir_" + secrets.token_hex(24)
    return raw, _hash_key(raw), raw[:12]


def verify_api_key(
    x_api_key: str = Security(_api_key_scheme),
    db: Session = Depends(get_db),
) -> models.APIKey:
    key_hash = _hash_key(x_api_key)
    api_key = (
        db.query(models.APIKey)
        .filter(models.APIKey.key_hash == key_hash, models.APIKey.active == True)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=401, detail="Clé API invalide ou révoquée.")
    api_key.last_used_at = datetime.utcnow()
    db.commit()
    return api_key


def _hab_to_dict(h: models.Habilitation, today: date) -> dict:
    return {
        "id": h.id,
        "nom_prenom": h.nom_prenom,
        "statut": h.statut.label if h.statut else None,
        "statut_id": h.statut_id,
        "filiale": h.filiale.label if h.filiale else None,
        "filiale_id": h.filiale_id,
        "description": h.description.label if h.description else None,
        "description_id": h.description_id,
        "service": h.service.label if h.service else None,
        "service_id": h.service_id,
        "societe": h.societe.label if h.societe else None,
        "societe_id": h.societe_id,
        "role": h.role.label if h.role else None,
        "role_id": h.role_id,
        "domaine": h.domaine.label if h.domaine else None,
        "domaine_id": h.domaine_id,
        "date_octroi": str(h.date_octroi) if h.date_octroi else None,
        "date_attestation": str(h.date_attestation) if h.date_attestation else None,
        "attestation_expiree": (h.date_attestation < today) if h.date_attestation else None,
        "date_sensibilisation": str(h.date_sensibilisation) if h.date_sensibilisation else None,
        "sensibilisation_expiree": (h.date_sensibilisation < today) if h.date_sensibilisation else None,
        "custom_fields": {
            cf.custom_type.label: cf.custom_value.label if cf.custom_value else None
            for cf in h.custom_fields
        },
        "created_at": h.created_at.isoformat() if h.created_at else None,
        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
    }


@router.get("/habilitations", summary="Lister les habilitations")
async def list_habilitations(
    q: Optional[str] = Query(None, description="Recherche sur le nom/prénom"),
    statut_id: Optional[int] = Query(None),
    domaine_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    societe_id: Optional[int] = Query(None),
    filiale_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    _: models.APIKey = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    query = db.query(models.Habilitation)
    if q:
        query = query.filter(models.Habilitation.nom_prenom.ilike(f"%{q}%"))
    if statut_id:
        query = query.filter(models.Habilitation.statut_id == statut_id)
    if domaine_id:
        query = query.filter(models.Habilitation.domaine_id == domaine_id)
    if service_id:
        query = query.filter(models.Habilitation.service_id == service_id)
    if societe_id:
        query = query.filter(models.Habilitation.societe_id == societe_id)
    if filiale_id:
        query = query.filter(models.Habilitation.filiale_id == filiale_id)
    if role_id:
        query = query.filter(models.Habilitation.role_id == role_id)

    total = query.count()
    items = (
        query.order_by(models.Habilitation.nom_prenom)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    today = date.today()
    return {
        "items": [_hab_to_dict(h, today) for h in items],
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "per_page": per_page,
    }


@router.get("/habilitations/{hab_id}", summary="Détail d'une habilitation")
async def get_habilitation(
    hab_id: int,
    _: models.APIKey = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habilitation introuvable.")
    return _hab_to_dict(h, date.today())


@router.get("/referentiels", summary="Lister tous les référentiels")
async def get_referentiels(
    _: models.APIKey = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    def _items(model):
        return [
            {"id": r.id, "label": r.label}
            for r in db.query(model).order_by(model.ordre, model.label).all()
        ]

    custom_types = (
        db.query(models.RefCustomType)
        .filter(models.RefCustomType.active == True)
        .order_by(models.RefCustomType.ordre, models.RefCustomType.label)
        .all()
    )
    custom = {
        ct.name: {
            "label": ct.label,
            "values": [{"id": v.id, "label": v.label} for v in ct.values],
        }
        for ct in custom_types
    }

    return {
        "statuts": [
            {"id": r.id, "label": r.label, "color": r.color}
            for r in db.query(models.RefStatut)
            .order_by(models.RefStatut.ordre, models.RefStatut.label)
            .all()
        ],
        "filiales": _items(models.RefFiliale),
        "descriptions": _items(models.RefDescription),
        "services": _items(models.RefService),
        "societes": _items(models.RefSociete),
        "roles": _items(models.RefRole),
        "domaines": _items(models.RefDomaine),
        "custom": custom,
    }
