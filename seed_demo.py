"""Script de données de démonstration — Groupe Meridia (fictif)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from app.database import SessionLocal
from app import models

db = SessionLocal()
today = date(2026, 5, 6)

# ── Référentiels ─────────────────────────────────────────────────────────────

def upsert(model, label, **kwargs):
    obj = db.query(model).filter_by(label=label).first()
    if not obj:
        obj = model(label=label, **kwargs)
        db.add(obj)
    return obj

# Domaines supplémentaires
upsert(models.RefDomaine, "Juridique", ordre=4)
upsert(models.RefDomaine, "Production", ordre=5)

# Filiales
for i, l in enumerate(["Meridia France", "Meridia Digital", "Meridia Industrie",
                        "Meridia Services", "Meridia International"], 1):
    upsert(models.RefFiliale, l, ordre=i)

# Sociétés
for i, l in enumerate(["Meridia SA", "Meridia Digital SAS",
                        "Meridia Industrie SARL", "MeriTech SAS"], 1):
    upsert(models.RefSociete, l, ordre=i)

# Services
for i, l in enumerate(["DSI", "Direction Financière", "Ressources Humaines",
                        "Production", "Commercial", "Juridique & Conformité"], 1):
    upsert(models.RefService, l, ordre=i)

# Descriptions
for i, l in enumerate([
    "Accès aux systèmes d'information",
    "Administration des bases de données",
    "Consultation des données financières",
    "Gestion des accès utilisateurs",
    "Audit et contrôle interne",
    "Développement applicatif",
    "Supervision des opérations industrielles",
], 1):
    upsert(models.RefDescription, l, ordre=i)

db.commit()

# ── Maps ──────────────────────────────────────────────────────────────────────

ST = {s.label: s for s in db.query(models.RefStatut).all()}
DO = {d.label: d for d in db.query(models.RefDomaine).all()}
RO = {r.label: r for r in db.query(models.RefRole).all()}
FI = {f.label: f for f in db.query(models.RefFiliale).all()}
SO = {s.label: s for s in db.query(models.RefSociete).all()}
SE = {s.label: s for s in db.query(models.RefService).all()}
DE = {d.label: d for d in db.query(models.RefDescription).all()}

# ── Habilitations ─────────────────────────────────────────────────────────────
# (nom_prenom, filiale, description, service, société, rôle, domaine, statut, octroi_delta, attest_delta)

DATA = [
    ("BERTRAND Sophie",     "Meridia France",        "Administration des bases de données",     "DSI",                    "Meridia SA",             "Administrateur", "Informatique", "Actif",    -730,  180),
    ("LEFEBVRE Marc",       "Meridia France",        "Consultation des données financières",    "Direction Financière",   "Meridia SA",             "Utilisateur",    "Finance",      "Actif",    -365,   90),
    ("MOREAU Isabelle",     "Meridia Digital",       "Gestion des accès utilisateurs",          "Ressources Humaines",    "Meridia Digital SAS",    "Lecteur",        "RH",           "Actif",    -180,  365),
    ("DUBOIS Thomas",       "Meridia Industrie",     "Accès aux systèmes d'information",        "DSI",                    "Meridia Industrie SARL", "Administrateur", "Informatique", "Suspendu", -400,  -10),
    ("PETIT Nathalie",      "Meridia France",        "Consultation des données financières",    "Direction Financière",   "Meridia SA",             "Utilisateur",    "Finance",      "Actif",    -200,  120),
    ("MARTIN Alexandre",    "Meridia Services",      "Développement applicatif",                "DSI",                    "Meridia SA",             "Utilisateur",    "Informatique", "Révoqué",  -900, -180),
    ("LEROY Caroline",      "Meridia Digital",       "Gestion des accès utilisateurs",          "Ressources Humaines",    "Meridia Digital SAS",    "Lecteur",        "RH",           "Actif",     -90,  275),
    ("BERNARD Julien",      "Meridia France",        "Audit et contrôle interne",               "Direction Financière",   "Meridia SA",             "Administrateur", "Finance",      "Actif",    -540,   60),
    ("ROUSSEAU Émilie",     "Meridia International", "Accès aux systèmes d'information",        "DSI",                    "MeriTech SAS",           "Lecteur",        "Informatique", "Actif",    -120,  240),
    ("FONTAINE Pierre",     "Meridia Services",      "Gestion des accès utilisateurs",          "Ressources Humaines",    "Meridia SA",             "Utilisateur",    "RH",           "Actif",    -300,   45),
    ("MERCIER Aurélie",     "Meridia Industrie",     "Consultation des données financières",    "Direction Financière",   "Meridia Industrie SARL", "Lecteur",        "Finance",      "Suspendu", -450,  -30),
    ("GARNIER François",    "Meridia France",        "Administration des bases de données",     "DSI",                    "Meridia SA",             "Administrateur", "Informatique", "Actif",    -600,  200),
    ("DUPONT Sandrine",     "Meridia Digital",       "Gestion des accès utilisateurs",          "Ressources Humaines",    "Meridia Digital SAS",    "Administrateur", "RH",           "Actif",    -250,  150),
    ("LAMBERT Nicolas",     "Meridia International", "Consultation des données financières",    "Direction Financière",   "MeriTech SAS",           "Utilisateur",    "Finance",      "Actif",    -180,  300),
    ("SIMON Céline",        "Meridia Industrie",     "Développement applicatif",                "DSI",                    "Meridia Industrie SARL", "Lecteur",        "Informatique", "Révoqué", -1100, -365),
    ("LECONTE Antoine",     "Meridia France",        "Audit et contrôle interne",               "Juridique & Conformité", "Meridia SA",             "Lecteur",        "Juridique",    "Actif",     -60,  400),
    ("BLANC Véronique",     "Meridia Services",      "Accès aux systèmes d'information",        "Commercial",             "Meridia SA",             "Utilisateur",    "Informatique", "Actif",    -730,   -5),
    ("FAURE Romain",        "Meridia Digital",       "Développement applicatif",                "DSI",                    "Meridia Digital SAS",    "Administrateur", "Informatique", "Actif",    -150,  500),
    ("PERRIN Laetitia",     "Meridia International", "Gestion des accès utilisateurs",          "Ressources Humaines",    "MeriTech SAS",           "Utilisateur",    "RH",           "Actif",    -200,  -20),
    ("RENARD Mathieu",      "Meridia France",        "Administration des bases de données",     "DSI",                    "Meridia SA",             "Utilisateur",    "Informatique", "Actif",     -45,  730),
]

admin = db.query(models.User).filter_by(username="admin").first()

for nom_prenom, fil, desc, svc, soc, role, dom, statut, od, ad in DATA:
    if db.query(models.Habilitation).filter_by(nom_prenom=nom_prenom).first():
        continue
    h = models.Habilitation(
        nom_prenom=nom_prenom,
        filiale_id=FI[fil].id,
        description_id=DE[desc].id,
        service_id=SE[svc].id,
        societe_id=SO[soc].id,
        role_id=RO[role].id,
        domaine_id=DO[dom].id,
        statut_id=ST[statut].id,
        date_octroi=today + timedelta(days=od),
        date_attestation=today + timedelta(days=ad),
        created_by=admin.id if admin else None,
        updated_by=admin.id if admin else None,
    )
    db.add(h)

db.commit()
db.close()

total = len(DATA)
print(f"✓ {total} habilitations créées (Groupe Meridia).")
print("  - Actif : 13  |  Suspendu : 2  |  Révoqué : 2")
print("  - Écarts d'attestations (expirés) : 6 entrées")
