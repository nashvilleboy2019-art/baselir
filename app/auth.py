import secrets
import bcrypt
from sqlalchemy.orm import Session
from app import models

try:
    from ldap3 import Server, Connection, SIMPLE, Tls, ALL
    import ssl
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

DEFAULT_PASSWORD = "noukiebogosse2026"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _get_cfg(db: Session, key: str, default: str = "") -> str:
    item = db.query(models.AppConfig).filter(models.AppConfig.key == key).first()
    return item.value if item and item.value is not None else default


def _domain_to_base_dn(domain: str) -> str:
    """company.local  →  dc=company,dc=local"""
    return ",".join(f"dc={part}" for part in domain.split(".") if part)


def ldap_authenticate(db: Session, username: str, password: str):
    if not LDAP_AVAILABLE:
        return None
    if _get_cfg(db, "ldap_enabled", "0") != "1":
        return None

    server_host    = _get_cfg(db, "ldap_server")
    port           = int(_get_cfg(db, "ldap_port", "389"))
    domain         = _get_cfg(db, "ldap_domain")
    use_tls        = _get_cfg(db, "ldap_tls", "0") == "1"
    base_dn        = _get_cfg(db, "ldap_base_dn") or _domain_to_base_dn(domain)
    allowed_ou     = _get_cfg(db, "ldap_allowed_ou", "").strip()    # doit figurer dans le DN
    allowed_group  = _get_cfg(db, "ldap_allowed_group", "").strip() # doit être dans memberOf

    if not server_host or not domain:
        return None

    try:
        tls_cfg = Tls(validate=ssl.CERT_NONE) if use_tls else None
        srv  = Server(server_host, port=port, use_ssl=use_tls, tls=tls_cfg, get_info=ALL)
        conn = Connection(srv, user=f"{username}@{domain}", password=password,
                          authentication=SIMPLE, auto_bind=True)

        # --- Vérification OU et/ou groupe ---
        if allowed_ou or allowed_group:
            conn.search(
                search_base=base_dn,
                search_filter=f"(sAMAccountName={username})",
                attributes=["distinguishedName", "memberOf"],
            )
            if not conn.entries:
                conn.unbind()
                return None  # compte non trouvé dans l'annuaire

            entry       = conn.entries[0]
            user_dn     = str(entry.distinguishedName).lower() if entry.distinguishedName else ""
            member_of   = [str(g).lower() for g in (entry.memberOf or [])]

            # Restriction par OU : le DN de l'utilisateur doit contenir le chemin OU
            if allowed_ou and allowed_ou.lower() not in user_dn:
                conn.unbind()
                return None  # utilisateur hors de l'OU autorisée

            # Restriction par groupe AD : l'utilisateur doit être membre du groupe
            if allowed_group and not any(allowed_group.lower() in g for g in member_of):
                conn.unbind()
                return None  # utilisateur non membre du groupe autorisé

        conn.unbind()

        # Authentification AD réussie — créer le compte local si absent
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            user = models.User(
                username=username,
                password_hash=hash_password(secrets.token_hex(32)),
                role="auditeur",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    except Exception:
        return None


def authenticate_user(db: Session, username: str, password: str):
    user = ldap_authenticate(db, username, password)
    if user:
        return user
    local = db.query(models.User).filter(models.User.username == username).first()
    if not local or not verify_password(password, local.password_hash):
        return None
    return local


def create_default_data(db: Session):
    if db.query(models.User).count() == 0:
        db.add_all([
            models.User(username="admin",
                        password_hash=hash_password(DEFAULT_PASSWORD),
                        role="responsable"),
            models.User(username="auditeur",
                        password_hash=hash_password(DEFAULT_PASSWORD),
                        role="auditeur"),
        ])
        db.commit()
        print(f"Utilisateurs par défaut créés : admin / {DEFAULT_PASSWORD}  |  auditeur / {DEFAULT_PASSWORD}")
        print("IMPORTANT : changez ces mots de passe après la première connexion.")

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
