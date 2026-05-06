import bcrypt
from sqlalchemy.orm import Session
from app import models


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_default_data(db: Session):
    # Utilisateurs par défaut
    if db.query(models.User).count() == 0:
        db.add_all([
            models.User(username="admin", password_hash=hash_password("admin123"), role="responsable"),
            models.User(username="auditeur", password_hash=hash_password("audit123"), role="auditeur"),
        ])
        db.commit()
        print("Utilisateurs par défaut créés : admin / admin123  |  auditeur / audit123")
        print("IMPORTANT : changez ces mots de passe après la première connexion.")

    # Référentiels par défaut
    if db.query(models.RefStatut).count() == 0:
        db.add_all([
            models.RefStatut(label="Actif", color="green", ordre=1),
            models.RefStatut(label="Suspendu", color="yellow", ordre=2),
            models.RefStatut(label="Révoqué", color="red", ordre=3),
        ])

    if db.query(models.RefDomaine).count() == 0:
        db.add_all([
            models.RefDomaine(label="Informatique", ordre=1),
            models.RefDomaine(label="Finance", ordre=2),
            models.RefDomaine(label="RH", ordre=3),
        ])

    if db.query(models.RefRole).count() == 0:
        db.add_all([
            models.RefRole(label="Administrateur", ordre=1),
            models.RefRole(label="Utilisateur", ordre=2),
            models.RefRole(label="Lecteur", ordre=3),
        ])

    db.commit()
