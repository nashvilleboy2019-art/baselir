# BaseLIR — Base de Liaisons Individus-Rôles

Application web de gestion des habilitations au sein d'une organisation. Remplace un fichier Excel de suivi des personnes habilitées à intervenir sur un domaine avec un rôle spécifique.

## Fonctionnalités

- **Gestion des habilitations** : Création, modification, suppression avec tous les champs métiers
- **Page d'audit** : Détection automatique des écarts (attestations expirées)
- **Référentiels personnalisables** : Statuts, Filiales, Descriptions, Services, Sociétés, Rôles, Domaines
- **Gestion des utilisateurs** : Deux rôles — Responsable (accès complet) et Auditeur (lecture seule)
- **Versioning** : Historique complet des modifications (avant/après) sur chaque habilitation
- **Journal d'activité** : Traçabilité de toutes les actions utilisateurs
- **Filtres et recherche** : Filtrage multicritères sur la liste des habilitations

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | FastAPI + Python |
| ORM | SQLAlchemy |
| Base de données | SQLite |
| Templates | Jinja2 |
| CSS | Tailwind CSS (CDN) |
| Sessions | itsdangerous (SessionMiddleware) |
| Mots de passe | bcrypt |

## Structure du projet

```
BaseLIR/
├── app/
│   ├── main.py              # Application FastAPI, routes principales
│   ├── models.py            # Modèles SQLAlchemy
│   ├── database.py          # Connexion SQLite
│   ├── auth.py              # Authentification + données par défaut
│   ├── utils.py             # Helpers (login, flash, pagination, historique)
│   ├── templates_config.py  # Configuration Jinja2
│   └── routers/
│       ├── habilitations.py # CRUD habilitations
│       ├── admin.py         # Gestion des référentiels
│       ├── audit.py         # Page écarts
│       ├── users.py         # Gestion utilisateurs
│       └── activity.py      # Journal d'activité
├── templates/               # Templates HTML (Jinja2)
├── static/                  # Fichiers statiques
├── data/                    # Base de données SQLite (auto-créé)
├── requirements.txt
├── run.py                   # Point d'entrée
└── install.txt              # Guide d'installation
```

## Installation rapide

```bash
# Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate    # Linux/macOS

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python run.py
```

Ouvrir : http://localhost:8001

## Comptes par défaut

| Identifiant | Mot de passe | Rôle |
|-------------|-------------|------|
| admin | admin123 | Responsable |
| auditeur | audit123 | Auditeur |

> **Important** : Changer ces mots de passe dès la première connexion.

## Champs d'une habilitation

| Champ | Description |
|-------|-------------|
| Statut | État de l'habilitation (personnalisable, avec couleur) |
| Nom et Prénom | Identité de la personne habilitée |
| Filiale du Groupe | Filiale de rattachement (personnalisable) |
| Description | Nature de la mission (personnalisable) |
| Service | Service ou département (personnalisable) |
| Société | Entité juridique (personnalisable) |
| Rôle | Rôle accordé (personnalisable) |
| Domaine | Périmètre fonctionnel (personnalisable) |
| Date d'octroi | Date d'attribution de l'habilitation |
| Date des attestations | Date limite — génère un écart si dépassée |

## Sécurité en production

Modifier la clé de session dans `app/main.py` :
```python
app.add_middleware(SessionMiddleware, secret_key="VOTRE_CLE_SECRETE_ICI")
```

Générer une clé sécurisée :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Licence

Usage interne — tous droits réservés.
