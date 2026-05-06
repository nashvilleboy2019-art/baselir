from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.utils import require_responsable, log_activity, set_flash, get_flash
from app.templates_config import templates

router = APIRouter()

REF_MAP = {
    "statuts": (models.RefStatut, "Statut"),
    "filiales": (models.RefFiliale, "Filiale"),
    "descriptions": (models.RefDescription, "Description"),
    "services": (models.RefService, "Service"),
    "societes": (models.RefSociete, "Société"),
    "roles": (models.RefRole, "Rôle"),
    "domaines": (models.RefDomaine, "Domaine"),
}

STATUT_COLORS = ["green", "yellow", "red", "blue", "purple", "orange", "gray", "teal", "pink"]


@router.get("/referentiels", response_class=HTMLResponse)
async def referentiels(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)

    data = {}
    for key, (model_cls, _) in REF_MAP.items():
        data[key] = db.query(model_cls).order_by(model_cls.ordre, model_cls.label).all()

    return templates.TemplateResponse(request, "admin/referentiels.html", {
        "user": user,
        "active": "admin",
        "flash": get_flash(request),
        "data": data,
        "ref_map": REF_MAP,
        "statut_colors": STATUT_COLORS,
    })


@router.post("/referentiels/{ref_type}/add")
async def add_ref(
    ref_type: str,
    request: Request,
    db: Session = Depends(get_db),
    label: str = Form(...),
    color: str = Form("gray"),
    ordre: str = Form("0"),
):
    user = require_responsable(request, db)
    if ref_type not in REF_MAP:
        raise HTTPException(status_code=404)

    model_cls, type_label = REF_MAP[ref_type]
    label = label.strip()
    if not label:
        set_flash(request, "Le libellé est requis.", "error")
        return RedirectResponse("/admin/referentiels", status_code=302)

    existing = db.query(model_cls).filter(model_cls.label == label).first()
    if existing:
        set_flash(request, f"« {label} » existe déjà.", "error")
        return RedirectResponse("/admin/referentiels", status_code=302)

    kwargs = {"label": label, "ordre": int(ordre) if ordre.isdigit() else 0}
    if ref_type == "statuts":
        kwargs["color"] = color if color in STATUT_COLORS else "gray"

    db.add(model_cls(**kwargs))
    log_activity(db, user, f"Ajout référentiel {type_label}", ref_type, None, label)
    db.commit()

    set_flash(request, f"« {label} » ajouté aux {type_label}s.")
    return RedirectResponse("/admin/referentiels", status_code=302)


@router.post("/referentiels/{ref_type}/{ref_id}/edit")
async def edit_ref(
    ref_type: str,
    ref_id: int,
    request: Request,
    db: Session = Depends(get_db),
    label: str = Form(...),
    color: str = Form("gray"),
    ordre: str = Form("0"),
):
    user = require_responsable(request, db)
    if ref_type not in REF_MAP:
        raise HTTPException(status_code=404)

    model_cls, type_label = REF_MAP[ref_type]
    item = db.query(model_cls).filter(model_cls.id == ref_id).first()
    if not item:
        raise HTTPException(status_code=404)

    label = label.strip()
    if not label:
        set_flash(request, "Le libellé est requis.", "error")
        return RedirectResponse("/admin/referentiels", status_code=302)

    dup = db.query(model_cls).filter(model_cls.label == label, model_cls.id != ref_id).first()
    if dup:
        set_flash(request, f"« {label} » existe déjà.", "error")
        return RedirectResponse("/admin/referentiels", status_code=302)

    item.label = label
    item.ordre = int(ordre) if ordre.isdigit() else 0
    if ref_type == "statuts" and hasattr(item, "color"):
        item.color = color if color in STATUT_COLORS else "gray"

    log_activity(db, user, f"Modification référentiel {type_label}", ref_type, ref_id, label)
    db.commit()

    set_flash(request, f"« {label} » mis à jour.")
    return RedirectResponse("/admin/referentiels", status_code=302)


@router.post("/referentiels/{ref_type}/{ref_id}/delete")
async def delete_ref(
    ref_type: str,
    ref_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_responsable(request, db)
    if ref_type not in REF_MAP:
        raise HTTPException(status_code=404)

    model_cls, type_label = REF_MAP[ref_type]
    item = db.query(model_cls).filter(model_cls.id == ref_id).first()
    if not item:
        raise HTTPException(status_code=404)

    label = item.label
    log_activity(db, user, f"Suppression référentiel {type_label}", ref_type, ref_id, label)
    db.delete(item)
    db.commit()

    set_flash(request, f"« {label} » supprimé.")
    return RedirectResponse("/admin/referentiels", status_code=302)
