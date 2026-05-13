from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import json
import os

from app.database import get_db, engine
from sqlalchemy import text
from app import models, auth, theme_cache
from app.routers import habilitations, admin, audit, users, activity, import_hab, api_v1
from app.templates_config import templates
from app.utils import get_flash, log_activity, require_login, get_config

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BaseLIR - Gestion des Habilitations")
app.add_middleware(SessionMiddleware, secret_key="baselir-change-this-secret-key-in-production")

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

static_dir      = os.path.join(PARENT_DIR, "static")
uploads_dir     = os.path.join(PARENT_DIR, "uploads")
screenshots_dir = os.path.join(PARENT_DIR, "screenshots")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(screenshots_dir, exist_ok=True)

app.mount("/static",      StaticFiles(directory=static_dir),      name="static")
app.mount("/uploads",     StaticFiles(directory=uploads_dir),     name="uploads")
app.mount("/screenshots", StaticFiles(directory=screenshots_dir), name="screenshots")

app.include_router(habilitations.router, prefix="/habilitations")
app.include_router(admin.router, prefix="/admin")
app.include_router(audit.router, prefix="/audit")
app.include_router(users.router, prefix="/users")
app.include_router(activity.router, prefix="/activity")
app.include_router(import_hab.router, prefix="/import")
app.include_router(api_v1.router, prefix="/api/v1", tags=["API v1"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=302)
    if exc.status_code == 403:
        return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Accès refusé</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 flex items-center justify-center h-screen">
<div class="text-center">
  <div class="text-6xl font-bold text-red-400 mb-4">403</div>
  <h1 class="text-2xl font-semibold text-gray-700 mb-2">Accès refusé</h1>
  <p class="text-gray-500 mb-6">{exc.detail or "Vous n'avez pas les droits nécessaires."}</p>
  <a href="/" class="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700">Retour</a>
</div></body></html>""", status_code=403)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.on_event("startup")
async def startup_event():
    with engine.connect() as conn:
        for table, col, typedef in [
            ("habilitations", "attestation_filename", "VARCHAR(255)"),
            ("users",         "nom",                 "VARCHAR(100)"),
            ("users",         "prenom",              "VARCHAR(100)"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))
                conn.commit()
            except Exception:
                pass

    db = next(get_db())
    try:
        auth.create_default_data(db)
        primary = get_config(db, "theme_primary", "teal")
        secondary = get_config(db, "theme_secondary", "orange")
        theme_cache.update(primary, secondary)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    today = date.today()

    total = db.query(func.count(models.Habilitation.id)).scalar() or 0
    expired_count = (db.query(func.count(models.Habilitation.id))
                     .filter(models.Habilitation.date_attestation < today).scalar() or 0)

    by_domaine = (
        db.query(models.RefDomaine.label, func.count(models.Habilitation.id))
        .outerjoin(models.Habilitation, models.Habilitation.domaine_id == models.RefDomaine.id)
        .group_by(models.RefDomaine.label)
        .order_by(func.count(models.Habilitation.id).desc()).all()
    )
    by_statut = (
        db.query(models.RefStatut.label, models.RefStatut.color, func.count(models.Habilitation.id))
        .outerjoin(models.Habilitation, models.Habilitation.statut_id == models.RefStatut.id)
        .group_by(models.RefStatut.label, models.RefStatut.color).all()
    )
    by_user = (
        db.query(models.User.username, models.User.role, func.count(models.Habilitation.id))
        .outerjoin(models.Habilitation, models.Habilitation.created_by == models.User.id)
        .group_by(models.User.username, models.User.role)
        .order_by(func.count(models.Habilitation.id).desc()).all()
    )
    by_societe = (
        db.query(models.RefSociete.label, func.count(models.Habilitation.id))
        .outerjoin(models.Habilitation, models.Habilitation.societe_id == models.RefSociete.id)
        .group_by(models.RefSociete.label)
        .order_by(func.count(models.Habilitation.id).desc()).all()
    )
    recent = (db.query(models.Habilitation)
              .order_by(models.Habilitation.updated_at.desc()).limit(10).all())
    recent_activity = (db.query(models.ActivityLog)
                       .order_by(models.ActivityLog.timestamp.desc()).limit(10).all())

    users_actifs = sum(1 for _, _, c in by_user if c > 0)
    societes_actives = sum(1 for _, c in by_societe if c > 0)
    domaines_actifs = sum(1 for _, c in by_domaine if c > 0)
    taux_conformite = round((total - expired_count) / total * 100) if total > 0 else 100

    stats_user = json.dumps([{"label": r[0], "role": r[1], "count": r[2]} for r in by_user if r[2] > 0])
    stats_societe = json.dumps([{"label": r[0], "count": r[1]} for r in by_societe if r[1] > 0])
    stats_domaine = json.dumps([{"label": r[0], "count": r[1]} for r in by_domaine if r[1] > 0])
    stats_statut = json.dumps([{"label": r[0], "color": r[1], "count": r[2]} for r in by_statut if r[2] > 0])

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user, "active": "dashboard", "flash": get_flash(request),
        "total": total, "expired_count": expired_count,
        "by_domaine": by_domaine, "by_statut": by_statut,
        "by_user": by_user, "by_societe": by_societe,
        "users_actifs": users_actifs, "societes_actives": societes_actives,
        "domaines_actifs": domaines_actifs, "taux_conformite": taux_conformite,
        "stats_user": stats_user, "stats_societe": stats_societe,
        "stats_domaine": stats_domaine, "stats_statut": stats_statut,
        "recent": recent, "recent_activity": recent_activity, "today": today,
    })


@app.get("/guide", response_class=HTMLResponse)
async def guide(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    return templates.TemplateResponse(request, "guide.html", {"user": user, "active": "guide"})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)
    logo = get_config(db, "logo_filename", "")
    ldap_enabled = get_config(db, "ldap_enabled", "0") == "1"
    return templates.TemplateResponse(request, "login.html",
                                      {"error": None, "logo": logo, "ldap_enabled": ldap_enabled})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = auth.authenticate_user(db, username, password)
    if not user:
        logo = get_config(db, "logo_filename", "")
        ldap_enabled = get_config(db, "ldap_enabled", "0") == "1"
        return templates.TemplateResponse(request, "login.html",
                                          {"error": "Identifiants incorrects",
                                           "logo": logo, "ldap_enabled": ldap_enabled})
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    log_activity(db, user, "Connexion")
    db.commit()
    return RedirectResponse("/", status_code=302)


@app.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if db_user:
            log_activity(db, db_user, "Déconnexion")
            db.commit()
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
