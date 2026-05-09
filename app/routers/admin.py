import os
import shutil
from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, theme_cache
from app.utils import require_responsable, log_activity, set_flash, get_flash, get_config, set_config
from app.templates_config import templates

router = APIRouter()

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.path.join(PARENT_DIR, "uploads")

REF_MAP = {
    "statuts":      (models.RefStatut,      "Statut"),
    "filiales":     (models.RefFiliale,     "Filiale"),
    "descriptions": (models.RefDescription, "Description"),
    "services":     (models.RefService,     "Service"),
    "societes":     (models.RefSociete,     "Société"),
    "roles":        (models.RefRole,        "Rôle"),
    "domaines":     (models.RefDomaine,     "Domaine"),
}

STATUT_COLORS = ["green", "yellow", "red", "blue", "purple", "orange", "gray", "teal", "pink"]


# ── Référentiels fixes ──────────────────────────────────────────────────────

@router.get("/referentiels", response_class=HTMLResponse)
async def referentiels(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    data = {k: db.query(m).order_by(m.ordre, m.label).all() for k, (m, _) in REF_MAP.items()}
    custom_types = db.query(models.RefCustomType).order_by(models.RefCustomType.ordre, models.RefCustomType.label).all()
    return templates.TemplateResponse(request, "admin/referentiels.html", {
        "user": user, "active": "admin", "flash": get_flash(request),
        "data": data, "ref_map": REF_MAP, "statut_colors": STATUT_COLORS,
        "custom_types": custom_types,
    })


@router.post("/referentiels/{ref_type}/add")
async def add_ref(ref_type: str, request: Request, db: Session = Depends(get_db),
                  label: str = Form(...), color: str = Form("gray"), ordre: str = Form("0")):
    user = require_responsable(request, db)
    if ref_type not in REF_MAP:
        raise HTTPException(status_code=404)
    model_cls, type_label = REF_MAP[ref_type]
    label = label.strip()
    if not label:
        set_flash(request, "Le libellé est requis.", "error")
        return RedirectResponse("/admin/referentiels", status_code=302)
    if db.query(model_cls).filter(model_cls.label == label).first():
        set_flash(request, f"« {label} » existe déjà.", "error")
        return RedirectResponse("/admin/referentiels", status_code=302)
    kwargs = {"label": label, "ordre": int(ordre) if ordre.isdigit() else 0}
    if ref_type == "statuts":
        kwargs["color"] = color if color in STATUT_COLORS else "gray"
    db.add(model_cls(**kwargs))
    log_activity(db, user, f"Ajout référentiel {type_label}", ref_type, None, label)
    db.commit()
    set_flash(request, f"« {label} » ajouté.")
    return RedirectResponse("/admin/referentiels", status_code=302)


@router.post("/referentiels/{ref_type}/{ref_id}/edit")
async def edit_ref(ref_type: str, ref_id: int, request: Request, db: Session = Depends(get_db),
                   label: str = Form(...), color: str = Form("gray"), ordre: str = Form("0")):
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
    if db.query(model_cls).filter(model_cls.label == label, model_cls.id != ref_id).first():
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
async def delete_ref(ref_type: str, ref_id: int, request: Request, db: Session = Depends(get_db)):
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


# ── Référentiels dynamiques (champs personnalisés) ─────────────────────────

@router.post("/custom-types/add")
async def add_custom_type(request: Request, db: Session = Depends(get_db),
                          label: str = Form(...), name: str = Form(...), ordre: str = Form("0")):
    user = require_responsable(request, db)
    label, name = label.strip(), name.strip().lower().replace(" ", "_")
    if not label or not name:
        set_flash(request, "Libellé et nom technique requis.", "error")
        return RedirectResponse("/admin/referentiels#custom", status_code=302)
    if db.query(models.RefCustomType).filter(models.RefCustomType.name == name).first():
        set_flash(request, f"Le champ « {name} » existe déjà.", "error")
        return RedirectResponse("/admin/referentiels#custom", status_code=302)
    db.add(models.RefCustomType(name=name, label=label, ordre=int(ordre) if ordre.isdigit() else 0))
    log_activity(db, user, "Ajout champ personnalisé", "custom_type", None, label)
    db.commit()
    set_flash(request, f"Champ « {label} » créé.")
    return RedirectResponse("/admin/referentiels#custom", status_code=302)


@router.post("/custom-types/{type_id}/edit")
async def edit_custom_type(type_id: int, request: Request, db: Session = Depends(get_db),
                           label: str = Form(...), ordre: str = Form("0")):
    user = require_responsable(request, db)
    ct = db.query(models.RefCustomType).filter(models.RefCustomType.id == type_id).first()
    if not ct:
        raise HTTPException(status_code=404)
    ct.label = label.strip()
    ct.ordre = int(ordre) if ordre.isdigit() else 0
    log_activity(db, user, "Modification champ personnalisé", "custom_type", type_id, ct.label)
    db.commit()
    set_flash(request, f"Champ « {ct.label} » mis à jour.")
    return RedirectResponse("/admin/referentiels#custom", status_code=302)


@router.post("/custom-types/{type_id}/delete")
async def delete_custom_type(type_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    ct = db.query(models.RefCustomType).filter(models.RefCustomType.id == type_id).first()
    if not ct:
        raise HTTPException(status_code=404)
    label = ct.label
    log_activity(db, user, "Suppression champ personnalisé", "custom_type", type_id, label)
    db.delete(ct)
    db.commit()
    set_flash(request, f"Champ « {label} » supprimé avec ses valeurs.")
    return RedirectResponse("/admin/referentiels#custom", status_code=302)


@router.post("/custom-types/{type_id}/values/add")
async def add_custom_value(type_id: int, request: Request, db: Session = Depends(get_db),
                           label: str = Form(...), ordre: str = Form("0")):
    user = require_responsable(request, db)
    ct = db.query(models.RefCustomType).filter(models.RefCustomType.id == type_id).first()
    if not ct:
        raise HTTPException(status_code=404)
    label = label.strip()
    if not label:
        set_flash(request, "Le libellé est requis.", "error")
        return RedirectResponse("/admin/referentiels#custom", status_code=302)
    db.add(models.RefCustomValue(type_id=type_id, label=label,
                                 ordre=int(ordre) if ordre.isdigit() else 0))
    db.commit()
    set_flash(request, f"Valeur « {label} » ajoutée à {ct.label}.")
    return RedirectResponse("/admin/referentiels#custom", status_code=302)


@router.post("/custom-types/{type_id}/values/{value_id}/delete")
async def delete_custom_value(type_id: int, value_id: int, request: Request,
                              db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    val = db.query(models.RefCustomValue).filter(
        models.RefCustomValue.id == value_id,
        models.RefCustomValue.type_id == type_id
    ).first()
    if not val:
        raise HTTPException(status_code=404)
    label = val.label
    db.delete(val)
    db.commit()
    set_flash(request, f"Valeur « {label} » supprimée.")
    return RedirectResponse("/admin/referentiels#custom", status_code=302)


# ── Paramètres (LDAP + logo) ───────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    cfg = {
        "ldap_enabled":       get_config(db, "ldap_enabled", "0"),
        "ldap_server":        get_config(db, "ldap_server", ""),
        "ldap_port":          get_config(db, "ldap_port", "389"),
        "ldap_domain":        get_config(db, "ldap_domain", ""),
        "ldap_base_dn":       get_config(db, "ldap_base_dn", ""),
        "ldap_tls":           get_config(db, "ldap_tls", "0"),
        "ldap_allowed_ou":    get_config(db, "ldap_allowed_ou", ""),
        "ldap_allowed_group": get_config(db, "ldap_allowed_group", ""),
        "logo_filename":      get_config(db, "logo_filename", ""),
        "theme_primary":      get_config(db, "theme_primary", "teal"),
        "theme_secondary":    get_config(db, "theme_secondary", "orange"),
    }
    return templates.TemplateResponse(request, "admin/settings.html", {
        "user": user, "active": "settings", "flash": get_flash(request), "cfg": cfg,
        "primary_choices":   theme_cache.PRIMARY_CHOICES,
        "secondary_choices": theme_cache.SECONDARY_CHOICES,
        "swatch_hex":        theme_cache.SWATCH_HEX,
    })


@router.post("/settings/ldap")
async def save_ldap(
    request: Request, db: Session = Depends(get_db),
    ldap_enabled: str = Form("0"),
    ldap_server: str = Form(""),
    ldap_port: str = Form("389"),
    ldap_domain: str = Form(""),
    ldap_base_dn: str = Form(""),
    ldap_tls: str = Form("0"),
    ldap_allowed_ou: str = Form(""),
    ldap_allowed_group: str = Form(""),
):
    user = require_responsable(request, db)
    set_config(db, "ldap_enabled",       "1" if ldap_enabled == "1" else "0")
    set_config(db, "ldap_server",        ldap_server.strip())
    set_config(db, "ldap_port",          ldap_port.strip() or "389")
    set_config(db, "ldap_domain",        ldap_domain.strip())
    set_config(db, "ldap_base_dn",       ldap_base_dn.strip())
    set_config(db, "ldap_tls",           "1" if ldap_tls == "1" else "0")
    set_config(db, "ldap_allowed_ou",    ldap_allowed_ou.strip())
    set_config(db, "ldap_allowed_group", ldap_allowed_group.strip())
    log_activity(db, user, "Modification config LDAP")
    db.commit()
    set_flash(request, "Configuration LDAP enregistrée.")
    return RedirectResponse("/admin/settings", status_code=302)


@router.post("/settings/logo")
async def upload_logo(request: Request, db: Session = Depends(get_db),
                      logo: UploadFile = File(...)):
    user = require_responsable(request, db)
    ext = os.path.splitext(logo.filename or "")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"):
        set_flash(request, "Format non supporté (PNG, JPG, SVG, GIF, WEBP).", "error")
        return RedirectResponse("/admin/settings", status_code=302)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    # Remove old logo
    old = get_config(db, "logo_filename", "")
    if old:
        old_path = os.path.join(UPLOADS_DIR, old)
        if os.path.exists(old_path):
            os.remove(old_path)
    filename = f"logo{ext}"
    with open(os.path.join(UPLOADS_DIR, filename), "wb") as f:
        shutil.copyfileobj(logo.file, f)
    set_config(db, "logo_filename", filename)
    log_activity(db, user, "Upload logo", details=filename)
    db.commit()
    set_flash(request, "Logo mis à jour.")
    return RedirectResponse("/admin/settings", status_code=302)


@router.post("/settings/logo/delete")
async def delete_logo(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    old = get_config(db, "logo_filename", "")
    if old:
        old_path = os.path.join(UPLOADS_DIR, old)
        if os.path.exists(old_path):
            os.remove(old_path)
    set_config(db, "logo_filename", "")
    log_activity(db, user, "Suppression logo")
    db.commit()
    set_flash(request, "Logo supprimé.")
    return RedirectResponse("/admin/settings", status_code=302)


@router.post("/settings/reset-habilitations")
async def reset_habilitations(
    request: Request, db: Session = Depends(get_db),
    confirmation: str = Form(""),
):
    user = require_responsable(request, db)
    if confirmation.strip().lower() != "je confirme l'effacement des habilitations":
        set_flash(request, "Phrase de confirmation incorrecte. Aucune donnée supprimée.", "error")
        return RedirectResponse("/admin/settings", status_code=302)

    db.query(models.HabilitationHistory).delete(synchronize_session=False)
    db.query(models.HabilitationCustomField).delete(synchronize_session=False)
    db.query(models.Habilitation).delete(synchronize_session=False)
    db.commit()

    attestations_dir = os.path.join(UPLOADS_DIR, "attestations")
    if os.path.exists(attestations_dir):
        shutil.rmtree(attestations_dir)

    log_activity(db, user, "RESET — toutes les habilitations supprimées")
    db.commit()

    set_flash(request, "Toutes les habilitations ont été supprimées.")
    return RedirectResponse("/admin/settings", status_code=302)


@router.post("/settings/theme")
async def save_theme(
    request: Request, db: Session = Depends(get_db),
    theme_primary: str = Form("teal"),
    theme_secondary: str = Form("orange"),
):
    user = require_responsable(request, db)
    primary = theme_primary if theme_primary in theme_cache.VALID_COLORS else "teal"
    secondary = theme_secondary if theme_secondary in theme_cache.VALID_COLORS else "orange"
    set_config(db, "theme_primary", primary)
    set_config(db, "theme_secondary", secondary)
    theme_cache.update(primary, secondary)
    log_activity(db, user, "Modification thème", details=f"{primary}/{secondary}")
    db.commit()
    set_flash(request, f"Thème mis à jour.")
    return RedirectResponse("/admin/settings", status_code=302)
