from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import date
import json

from app.database import get_db
from app import models
from app.utils import (require_login, require_responsable, log_activity,
                       log_history, habilitation_to_dict, set_flash, get_flash, paginate)
from app.templates_config import templates

router = APIRouter()


def _get_referentiels(db: Session):
    return {
        "statuts": db.query(models.RefStatut).order_by(models.RefStatut.ordre, models.RefStatut.label).all(),
        "filiales": db.query(models.RefFiliale).order_by(models.RefFiliale.ordre, models.RefFiliale.label).all(),
        "descriptions": db.query(models.RefDescription).order_by(models.RefDescription.ordre, models.RefDescription.label).all(),
        "services": db.query(models.RefService).order_by(models.RefService.ordre, models.RefService.label).all(),
        "societes": db.query(models.RefSociete).order_by(models.RefSociete.ordre, models.RefSociete.label).all(),
        "roles": db.query(models.RefRole).order_by(models.RefRole.ordre, models.RefRole.label).all(),
        "domaines": db.query(models.RefDomaine).order_by(models.RefDomaine.ordre, models.RefDomaine.label).all(),
    }


@router.get("/", response_class=HTMLResponse)
async def list_habilitations(
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    q: str = "",
    statut_id: str = "",
    domaine_id: str = "",
    service_id: str = "",
    societe_id: str = "",
    filiale_id: str = "",
    role_id: str = "",
    ecarts_only: str = "",
):
    user = require_login(request, db)
    today = date.today()

    query = db.query(models.Habilitation)

    if q:
        query = query.filter(models.Habilitation.nom_prenom.ilike(f"%{q}%"))
    if statut_id:
        query = query.filter(models.Habilitation.statut_id == int(statut_id))
    if domaine_id:
        query = query.filter(models.Habilitation.domaine_id == int(domaine_id))
    if service_id:
        query = query.filter(models.Habilitation.service_id == int(service_id))
    if societe_id:
        query = query.filter(models.Habilitation.societe_id == int(societe_id))
    if filiale_id:
        query = query.filter(models.Habilitation.filiale_id == int(filiale_id))
    if role_id:
        query = query.filter(models.Habilitation.role_id == int(role_id))
    if ecarts_only:
        query = query.filter(models.Habilitation.date_attestation < today)

    query = query.order_by(models.Habilitation.nom_prenom)
    paged = paginate(query, page)
    refs = _get_referentiels(db)

    return templates.TemplateResponse(request, "habilitations/list.html", {
        "user": user,
        "active": "habilitations",
        "flash": get_flash(request),
        "paged": paged,
        "today": today,
        "q": q,
        "statut_id": statut_id,
        "domaine_id": domaine_id,
        "service_id": service_id,
        "societe_id": societe_id,
        "filiale_id": filiale_id,
        "role_id": role_id,
        "ecarts_only": ecarts_only,
        **refs,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_form(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    refs = _get_referentiels(db)
    return templates.TemplateResponse(request, "habilitations/form.html", {
        "user": user, "active": "habilitations",
        "target": None, "errors": {},
        **refs,
    })


@router.post("/new", response_class=HTMLResponse)
async def create_habilitation(
    request: Request,
    db: Session = Depends(get_db),
    nom_prenom: str = Form(...),
    statut_id: str = Form(""),
    filiale_id: str = Form(""),
    description_id: str = Form(""),
    service_id: str = Form(""),
    societe_id: str = Form(""),
    role_id: str = Form(""),
    domaine_id: str = Form(""),
    date_octroi: str = Form(""),
    date_attestation: str = Form(""),
    note: str = Form(""),
):
    user = require_responsable(request, db)
    refs = _get_referentiels(db)
    errors = {}

    nom_prenom = nom_prenom.strip()
    if not nom_prenom:
        errors["nom_prenom"] = "Le nom et prénom est requis."

    def parse_int(val):
        return int(val) if val else None

    def parse_date(val):
        if not val:
            return None
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None

    if errors:
        return templates.TemplateResponse(request, "habilitations/form.html", {
            "user": user, "active": "habilitations",
            "target": None, "errors": errors, **refs,
        })

    h = models.Habilitation(
        nom_prenom=nom_prenom,
        statut_id=parse_int(statut_id),
        filiale_id=parse_int(filiale_id),
        description_id=parse_int(description_id),
        service_id=parse_int(service_id),
        societe_id=parse_int(societe_id),
        role_id=parse_int(role_id),
        domaine_id=parse_int(domaine_id),
        date_octroi=parse_date(date_octroi),
        date_attestation=parse_date(date_attestation),
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(h)
    db.flush()

    log_history(db, h.id, "Création", user.id, new_values=habilitation_to_dict(h), note=note or None)
    log_activity(db, user, "Création habilitation", "habilitation", h.id, nom_prenom)
    db.commit()

    set_flash(request, f"Habilitation « {nom_prenom} » créée.")
    return RedirectResponse(f"/habilitations/{h.id}", status_code=302)


@router.get("/{hab_id}", response_class=HTMLResponse)
async def detail(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)
    today = date.today()
    return templates.TemplateResponse(request, "habilitations/detail.html", {
        "user": user, "active": "habilitations",
        "flash": get_flash(request),
        "h": h,
        "today": today,
        "expired": h.date_attestation and h.date_attestation < today,
    })


@router.get("/{hab_id}/edit", response_class=HTMLResponse)
async def edit_form(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)
    refs = _get_referentiels(db)
    return templates.TemplateResponse(request, "habilitations/form.html", {
        "user": user, "active": "habilitations",
        "target": h, "errors": {},
        **refs,
    })


@router.post("/{hab_id}/edit", response_class=HTMLResponse)
async def edit_habilitation(
    hab_id: int,
    request: Request,
    db: Session = Depends(get_db),
    nom_prenom: str = Form(...),
    statut_id: str = Form(""),
    filiale_id: str = Form(""),
    description_id: str = Form(""),
    service_id: str = Form(""),
    societe_id: str = Form(""),
    role_id: str = Form(""),
    domaine_id: str = Form(""),
    date_octroi: str = Form(""),
    date_attestation: str = Form(""),
    note: str = Form(""),
):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    refs = _get_referentiels(db)
    errors = {}
    nom_prenom = nom_prenom.strip()
    if not nom_prenom:
        errors["nom_prenom"] = "Le nom et prénom est requis."

    if errors:
        return templates.TemplateResponse(request, "habilitations/form.html", {
            "user": user, "active": "habilitations",
            "target": h, "errors": errors, **refs,
        })

    def parse_int(val):
        return int(val) if val else None

    def parse_date(val):
        if not val:
            return None
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None

    old = habilitation_to_dict(h)

    h.nom_prenom = nom_prenom
    h.statut_id = parse_int(statut_id)
    h.filiale_id = parse_int(filiale_id)
    h.description_id = parse_int(description_id)
    h.service_id = parse_int(service_id)
    h.societe_id = parse_int(societe_id)
    h.role_id = parse_int(role_id)
    h.domaine_id = parse_int(domaine_id)
    h.date_octroi = parse_date(date_octroi)
    h.date_attestation = parse_date(date_attestation)
    h.updated_by = user.id

    db.flush()
    new = habilitation_to_dict(h)

    log_history(db, h.id, "Modification", user.id, old_values=old, new_values=new, note=note or None)
    log_activity(db, user, "Modification habilitation", "habilitation", h.id, nom_prenom)
    db.commit()

    set_flash(request, f"Habilitation « {nom_prenom} » mise à jour.")
    return RedirectResponse(f"/habilitations/{h.id}", status_code=302)


@router.post("/{hab_id}/delete")
async def delete_habilitation(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    nom = h.nom_prenom
    log_activity(db, user, "Suppression habilitation", "habilitation", hab_id, nom)
    db.delete(h)
    db.commit()

    set_flash(request, f"Habilitation « {nom} » supprimée.")
    return RedirectResponse("/habilitations/", status_code=302)


@router.get("/{hab_id}/history", response_class=HTMLResponse)
async def history(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    entries = (db.query(models.HabilitationHistory)
               .filter(models.HabilitationHistory.habilitation_id == hab_id)
               .order_by(models.HabilitationHistory.changed_at.desc())
               .all())

    parsed = []
    for e in entries:
        parsed.append({
            "entry": e,
            "old": json.loads(e.old_values) if e.old_values else None,
            "new": json.loads(e.new_values) if e.new_values else None,
        })

    return templates.TemplateResponse(request, "habilitations/history.html", {
        "user": user, "active": "habilitations",
        "h": h,
        "entries": parsed,
    })
