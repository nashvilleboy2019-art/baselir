import csv
import io
import unicodedata
from datetime import date, datetime
from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.utils import require_responsable, log_activity, set_flash, get_flash
from app.templates_config import templates

router = APIRouter()

# Correspondance header normalisé → champ interne
COLUMN_MAP = {
    "nom et prenom":          "nom_prenom",
    "nom prenom":             "nom_prenom",
    "nom_prenom":             "nom_prenom",
    "prenom nom":             "nom_prenom",
    "nom":                    "nom_prenom",
    "statut":                 "statut",
    "filiale":                "filiale",
    "filiale du groupe":      "filiale",
    "description":            "description",
    "service":                "service",
    "societe":                "societe",
    "société":                "societe",
    "role":                   "role",
    "rôle":                   "role",
    "domaine":                "domaine",
    "date octroi":            "date_octroi",
    "date d octroi":          "date_octroi",
    "date_octroi":            "date_octroi",
    "date des attestations":  "date_attestation",
    "date attestation":       "date_attestation",
    "date_attestation":       "date_attestation",
}

REF_MODELS = {
    "statut":      models.RefStatut,
    "filiale":     models.RefFiliale,
    "description": models.RefDescription,
    "service":     models.RefService,
    "societe":     models.RefSociete,
    "role":        models.RefRole,
    "domaine":     models.RefDomaine,
}


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s


def _parse_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    val = str(val).strip()
    if not val:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    return None


def _get_or_create_ref(db: Session, model_cls, label: str):
    label = label.strip()
    if not label:
        return None
    item = db.query(model_cls).filter(model_cls.label == label).first()
    if not item:
        item = model_cls(label=label, ordre=0)
        db.add(item)
        db.flush()
    return item.id


def _read_csv(content: bytes) -> tuple[list[str], list[list]]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _read_xlsx(content: bytes) -> tuple[list[str], list[list]]:
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl non installé.")
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [str(c) if c is not None else "" for c in rows[0]]
    data = [list(r) for r in rows[1:]]
    return headers, data


@router.get("/", response_class=HTMLResponse)
async def import_page(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    return templates.TemplateResponse(request, "import/upload.html", {
        "user": user, "active": "import", "flash": get_flash(request),
    })


@router.get("/template")
async def download_template():
    from fastapi.responses import Response
    content = (
        "Nom et Prénom,Statut,Filiale du Groupe,Description,"
        "Service,Société,Rôle,Domaine,Date d'octroi,Date des attestations\r\n"
        "Jean Dupont,Actif,Filiale A,Consultant,DSI,Société A,"
        "Administrateur,Informatique,01/01/2024,31/12/2026\r\n"
    )
    return Response(content=content.encode("utf-8-sig"),
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=template_import.csv"})


@router.post("/", response_class=HTMLResponse)
async def process_import(request: Request, db: Session = Depends(get_db),
                          file: UploadFile = File(...)):
    user = require_responsable(request, db)
    content = await file.read()
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "csv":
        headers, rows = _read_csv(content)
    elif ext in ("xlsx", "xlsm"):
        headers, rows = _read_xlsx(content)
    else:
        set_flash(request, "Format non supporté. Utilisez CSV ou XLSX.", "error")
        return RedirectResponse("/import/", status_code=302)

    # Map headers to fields
    col_map = {}  # col_index → field_name
    for i, h in enumerate(headers):
        field = COLUMN_MAP.get(_norm(h))
        if field:
            col_map[i] = field

    if "nom_prenom" not in col_map.values():
        set_flash(request, "Colonne « Nom et Prénom » introuvable dans le fichier.", "error")
        return RedirectResponse("/import/", status_code=302)

    results = []
    created = 0
    errors = 0
    new_ref_values: list[str] = []

    for row_num, row in enumerate(rows, start=2):
        if not any(str(c).strip() for c in row if c is not None):
            continue  # skip empty rows

        row_data = {}
        for col_idx, field in col_map.items():
            val = row[col_idx] if col_idx < len(row) else None
            row_data[field] = val

        nom_prenom = str(row_data.get("nom_prenom") or "").strip()
        if not nom_prenom:
            results.append({"row": row_num, "status": "error",
                             "msg": "Nom et Prénom vide — ligne ignorée.", "nom": "—"})
            errors += 1
            continue

        try:
            # Resolve referentials (auto-create if missing)
            def resolve(field, model_cls):
                raw = str(row_data.get(field) or "").strip()
                if not raw:
                    return None
                existing = db.query(model_cls).filter(model_cls.label == raw).first()
                if not existing:
                    new_ref_values.append(f"{field}: {raw}")
                return _get_or_create_ref(db, model_cls, raw)

            h = models.Habilitation(
                nom_prenom=nom_prenom,
                statut_id=resolve("statut", models.RefStatut),
                filiale_id=resolve("filiale", models.RefFiliale),
                description_id=resolve("description", models.RefDescription),
                service_id=resolve("service", models.RefService),
                societe_id=resolve("societe", models.RefSociete),
                role_id=resolve("role", models.RefRole),
                domaine_id=resolve("domaine", models.RefDomaine),
                date_octroi=_parse_date(row_data.get("date_octroi")),
                date_attestation=_parse_date(row_data.get("date_attestation")),
                created_by=user.id,
                updated_by=user.id,
            )
            db.add(h)
            db.flush()
            results.append({"row": row_num, "status": "ok",
                             "msg": "Importé", "nom": nom_prenom})
            created += 1
        except Exception as e:
            db.rollback()
            results.append({"row": row_num, "status": "error",
                             "msg": str(e), "nom": nom_prenom})
            errors += 1
            continue

    db.commit()
    log_activity(db, user, "Import habilitations", details=f"{created} créées, {errors} erreurs")

    return templates.TemplateResponse(request, "import/result.html", {
        "user": user, "active": "import",
        "results": results, "created": created, "errors": errors,
        "new_ref_values": list(set(new_ref_values)),
        "filename": filename,
    })
