"""
Remet la base de données dans son état initial vierge.
Supprime toutes les habilitations, référentiels et config,
puis recrée les données par défaut (utilisateurs + 3 statuts/domaines/rôles).

Usage : python reset_db.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models, auth

db = SessionLocal()

tables_to_clear = [
    models.HabilitationCustomField,
    models.HabilitationHistory,
    models.Habilitation,
    models.RefCustomValue,
    models.RefCustomType,
    models.RefFiliale,
    models.RefDescription,
    models.RefService,
    models.RefSociete,
    models.RefRole,
    models.RefDomaine,
    models.RefStatut,
    models.ActivityLog,
    models.AppConfig,
]

for model in tables_to_clear:
    db.query(model).delete()

db.commit()
db.close()

db2 = SessionLocal()
auth.create_default_data(db2)
db2.close()

print("Base remise a zero. Comptes par defaut recrees : admin / auditeur.")
