from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
import json
import os
import shutil

from app.database import get_db
from app import models
from app.utils import (require_login, require_responsable, log_activity, log_history,
                       habilitation_to_dict, set_flash, get_flash, paginate,
                       get_custom_field_map, save_custom_fields)
from app.templates_config import templates

router = APIRouter()

UPLOADS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads"
)
ATTESTATIONS_DIR = os.path.join(UPLOADS_DIR, "attestations")
SENSIBILISATIONS_DIR = os.path.join(UPLOADS_DIR, "sensibilisations")
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}


def _get_referentiels(db: Session):
    return {
        "statuts":      db.query(models.RefStatut).order_by(models.RefStatut.ordre, models.RefStatut.label).all(),
        "filiales":     db.query(models.RefFiliale).order_by(models.RefFiliale.ordre, models.RefFiliale.label).all(),
        "descriptions": db.query(models.RefDescription).order_by(models.RefDescription.ordre, models.RefDescription.label).all(),
        "services":     db.query(models.RefService).order_by(models.RefService.ordre, models.RefService.label).all(),
        "societes":     db.query(models.RefSociete).order_by(models.RefSociete.ordre, models.RefSociete.label).all(),
        "roles":        db.query(models.RefRole).order_by(models.RefRole.ordre, models.RefRole.label).all(),
        "domaines":     db.query(models.RefDomaine).order_by(models.RefDomaine.ordre, models.RefDomaine.label).all(),
        "custom_types": db.query(models.RefCustomType).filter(models.RefCustomType.active == True)
                          .order_by(models.RefCustomType.ordre, models.RefCustomType.label).all(),
    }


def _parse_int(val):
    return int(val) if val else None


def _parse_date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


@router.get("/", response_class=HTMLResponse)
async def list_habilitations(
    request: Request, db: Session = Depends(get_db),
    page: int = 1, q: str = "", statut_id: str = "",
    domaine_id: str = "", service_id: str = "",
    societe_id: str = "", filiale_id: str = "",
    role_id: str = "", ecarts_only: str = "",
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
        "user": user, "active": "habilitations", "flash": get_flash(request),
        "paged": paged, "today": today, "q": q,
        "statut_id": statut_id, "domaine_id": domaine_id, "service_id": service_id,
        "societe_id": societe_id, "filiale_id": filiale_id, "role_id": role_id,
        "ecarts_only": ecarts_only, **refs,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_form(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    refs = _get_referentiels(db)
    return templates.TemplateResponse(request, "habilitations/form.html", {
        "user": user, "active": "habilitations",
        "target": None, "errors": {}, "custom_field_map": {}, **refs,
    })


@router.post("/new", response_class=HTMLResponse)
async def create_habilitation(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    refs = _get_referentiels(db)
    form = await request.form()
    errors = {}

    nom_prenom = form.get("nom_prenom", "").strip()
    if not nom_prenom:
        errors["nom_prenom"] = "Le nom et prénom est requis."
    if errors:
        return templates.TemplateResponse(request, "habilitations/form.html", {
            "user": user, "active": "habilitations",
            "target": None, "errors": errors, "custom_field_map": {}, **refs,
        })

    h = models.Habilitation(
        nom_prenom=nom_prenom,
        statut_id=_parse_int(form.get("statut_id", "")),
        filiale_id=_parse_int(form.get("filiale_id", "")),
        description_id=_parse_int(form.get("description_id", "")),
        service_id=_parse_int(form.get("service_id", "")),
        societe_id=_parse_int(form.get("societe_id", "")),
        role_id=_parse_int(form.get("role_id", "")),
        domaine_id=_parse_int(form.get("domaine_id", "")),
        date_octroi=_parse_date(form.get("date_octroi", "")),
        date_attestation=_parse_date(form.get("date_attestation", "")),
        date_sensibilisation=_parse_date(form.get("date_sensibilisation", "")),
        created_by=user.id, updated_by=user.id,
    )
    db.add(h)
    db.flush()

    # Custom fields
    custom_map = {ct.id: _parse_int(form.get(f"custom_{ct.id}", ""))
                  for ct in refs["custom_types"]}
    save_custom_fields(db, h.id, custom_map)
    db.refresh(h)

    log_history(db, h.id, "Création", user.id,
                new_values=habilitation_to_dict(h, h.custom_fields),
                note=form.get("note", "") or None)
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
        "user": user, "active": "habilitations", "flash": get_flash(request),
        "h": h, "today": today,
        "expired": h.date_attestation and h.date_attestation < today,
        "sensibilisation_expiree": h.date_sensibilisation and h.date_sensibilisation < today,
    })


@router.get("/{hab_id}/edit", response_class=HTMLResponse)
async def edit_form(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)
    refs = _get_referentiels(db)
    custom_field_map = get_custom_field_map(db, hab_id)
    return templates.TemplateResponse(request, "habilitations/form.html", {
        "user": user, "active": "habilitations",
        "target": h, "errors": {}, "custom_field_map": custom_field_map, **refs,
    })


@router.post("/{hab_id}/edit", response_class=HTMLResponse)
async def edit_habilitation(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    refs = _get_referentiels(db)
    form = await request.form()
    errors = {}

    nom_prenom = form.get("nom_prenom", "").strip()
    if not nom_prenom:
        errors["nom_prenom"] = "Le nom et prénom est requis."
    if errors:
        return templates.TemplateResponse(request, "habilitations/form.html", {
            "user": user, "active": "habilitations",
            "target": h, "errors": errors,
            "custom_field_map": get_custom_field_map(db, hab_id), **refs,
        })

    old = habilitation_to_dict(h, h.custom_fields)

    h.nom_prenom = nom_prenom
    h.statut_id = _parse_int(form.get("statut_id", ""))
    h.filiale_id = _parse_int(form.get("filiale_id", ""))
    h.description_id = _parse_int(form.get("description_id", ""))
    h.service_id = _parse_int(form.get("service_id", ""))
    h.societe_id = _parse_int(form.get("societe_id", ""))
    h.role_id = _parse_int(form.get("role_id", ""))
    h.domaine_id = _parse_int(form.get("domaine_id", ""))
    h.date_octroi = _parse_date(form.get("date_octroi", ""))
    h.date_attestation = _parse_date(form.get("date_attestation", ""))
    h.date_sensibilisation = _parse_date(form.get("date_sensibilisation", ""))
    h.updated_by = user.id

    custom_map = {ct.id: _parse_int(form.get(f"custom_{ct.id}", ""))
                  for ct in refs["custom_types"]}
    save_custom_fields(db, h.id, custom_map)
    db.flush()
    db.refresh(h)

    new = habilitation_to_dict(h, h.custom_fields)
    log_history(db, h.id, "Modification", user.id, old_values=old, new_values=new,
                note=form.get("note", "") or None)
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


@router.post("/{hab_id}/upload-attestation")
async def upload_attestation(
    hab_id: int, request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        set_flash(request, "Format non autorisé. Utilisez PDF, JPG, PNG ou DOCX.", "error")
        return RedirectResponse(f"/habilitations/{hab_id}", status_code=302)

    os.makedirs(ATTESTATIONS_DIR, exist_ok=True)
    safe_name = f"hab_{hab_id}{ext}"
    dest = os.path.join(ATTESTATIONS_DIR, safe_name)

    if h.attestation_filename and h.attestation_filename != safe_name:
        old = os.path.join(ATTESTATIONS_DIR, h.attestation_filename)
        if os.path.exists(old):
            os.remove(old)

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    h.attestation_filename = safe_name
    h.updated_by = user.id
    log_activity(db, user, "Upload preuve attestation", "habilitation", hab_id, h.nom_prenom)
    db.commit()

    set_flash(request, "Preuve d'attestation enregistrée.")
    return RedirectResponse(f"/habilitations/{hab_id}", status_code=302)


@router.post("/{hab_id}/delete-attestation")
async def delete_attestation(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    if h.attestation_filename:
        path = os.path.join(ATTESTATIONS_DIR, h.attestation_filename)
        if os.path.exists(path):
            os.remove(path)
        h.attestation_filename = None
        h.updated_by = user.id
        log_activity(db, user, "Suppression preuve attestation", "habilitation", hab_id, h.nom_prenom)
        db.commit()

    set_flash(request, "Preuve d'attestation supprimée.")
    return RedirectResponse(f"/habilitations/{hab_id}", status_code=302)


@router.post("/{hab_id}/upload-sensibilisation")
async def upload_sensibilisation(
    hab_id: int, request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        set_flash(request, "Format non autorisé. Utilisez PDF, JPG, PNG ou DOCX.", "error")
        return RedirectResponse(f"/habilitations/{hab_id}", status_code=302)

    os.makedirs(SENSIBILISATIONS_DIR, exist_ok=True)
    safe_name = f"sensi_{hab_id}{ext}"
    dest = os.path.join(SENSIBILISATIONS_DIR, safe_name)

    if h.sensibilisation_filename and h.sensibilisation_filename != safe_name:
        old = os.path.join(SENSIBILISATIONS_DIR, h.sensibilisation_filename)
        if os.path.exists(old):
            os.remove(old)

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    h.sensibilisation_filename = safe_name
    h.updated_by = user.id
    log_activity(db, user, "Upload sensibilisation SI", "habilitation", hab_id, h.nom_prenom)
    db.commit()

    set_flash(request, "Preuve de sensibilisation enregistrée.")
    return RedirectResponse(f"/habilitations/{hab_id}", status_code=302)


@router.post("/{hab_id}/delete-sensibilisation")
async def delete_sensibilisation(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)

    if h.sensibilisation_filename:
        path = os.path.join(SENSIBILISATIONS_DIR, h.sensibilisation_filename)
        if os.path.exists(path):
            os.remove(path)
        h.sensibilisation_filename = None
        h.updated_by = user.id
        log_activity(db, user, "Suppression preuve sensibilisation", "habilitation", hab_id, h.nom_prenom)
        db.commit()

    set_flash(request, "Preuve de sensibilisation supprimée.")
    return RedirectResponse(f"/habilitations/{hab_id}", status_code=302)


@router.get("/{hab_id}/history", response_class=HTMLResponse)
async def history(hab_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    h = db.query(models.Habilitation).filter(models.Habilitation.id == hab_id).first()
    if not h:
        raise HTTPException(status_code=404)
    entries = (db.query(models.HabilitationHistory)
               .filter(models.HabilitationHistory.habilitation_id == hab_id)
               .order_by(models.HabilitationHistory.changed_at.desc()).all())
    parsed = [{"entry": e,
               "old": json.loads(e.old_values) if e.old_values else None,
               "new": json.loads(e.new_values) if e.new_values else None}
              for e in entries]
    return templates.TemplateResponse(request, "habilitations/history.html", {
        "user": user, "active": "habilitations", "h": h, "entries": parsed,
    })
