from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from app.database import get_db
from app import models
from app.utils import require_login, get_flash
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def ecarts(
    request: Request,
    db: Session = Depends(get_db),
    domaine_id: str = "",
    service_id: str = "",
    societe_id: str = "",
):
    user = require_login(request, db)
    today = date.today()

    query = (db.query(models.Habilitation)
             .filter(models.Habilitation.date_attestation < today))

    if domaine_id:
        query = query.filter(models.Habilitation.domaine_id == int(domaine_id))
    if service_id:
        query = query.filter(models.Habilitation.service_id == int(service_id))
    if societe_id:
        query = query.filter(models.Habilitation.societe_id == int(societe_id))

    ecarts_list = query.order_by(models.Habilitation.date_attestation).all()

    # Stat: écarts par domaine
    by_domaine = (
        db.query(models.RefDomaine.label, func.count(models.Habilitation.id))
        .join(models.Habilitation, models.Habilitation.domaine_id == models.RefDomaine.id)
        .filter(models.Habilitation.date_attestation < today)
        .group_by(models.RefDomaine.label)
        .order_by(func.count(models.Habilitation.id).desc())
        .all()
    )

    # Sans date attestation (risque potentiel)
    sans_date = (db.query(func.count(models.Habilitation.id))
                 .filter(models.Habilitation.date_attestation == None)
                 .scalar() or 0)

    domaines = db.query(models.RefDomaine).order_by(models.RefDomaine.label).all()
    services = db.query(models.RefService).order_by(models.RefService.label).all()
    societes = db.query(models.RefSociete).order_by(models.RefSociete.label).all()

    return templates.TemplateResponse(request, "audit/ecarts.html", {
        "user": user,
        "active": "audit",
        "flash": get_flash(request),
        "ecarts_list": ecarts_list,
        "by_domaine": by_domaine,
        "sans_date": sans_date,
        "today": today,
        "total_ecarts": len(ecarts_list),
        "domaine_id": domaine_id,
        "service_id": service_id,
        "societe_id": societe_id,
        "domaines": domaines,
        "services": services,
        "societes": societes,
    })
