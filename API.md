# BaseLIR — Documentation API REST

L'API REST de BaseLIR permet à des applications externes d'interroger la base des habilitations en **lecture seule**.

---

## Authentification

Toutes les requêtes doivent inclure le header `X-API-Key` avec une clé générée depuis l'interface **Admin > API**.

```http
X-API-Key: lir_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Les clés ont le format `lir_` suivi de 48 caractères hexadécimaux. Elles sont stockées hachées en base (SHA-256) — le secret brut n'est affiché qu'à la création.

**Erreurs d'authentification :**

| Code | Signification |
|------|---------------|
| `401` | Clé absente, invalide ou révoquée |

---

## Base URL

```
http://<hôte>:<port>/api/v1
```

Exemple local : `http://localhost:8001/api/v1`

---

## Endpoints

### `GET /api/v1/habilitations`

Retourne une liste paginée d'habilitations, avec filtres optionnels.

#### Paramètres de requête

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `q` | string | — | Recherche partielle sur le nom/prénom (insensible à la casse) |
| `statut_id` | int | — | Filtrer par statut (ID issu de `/referentiels`) |
| `domaine_id` | int | — | Filtrer par domaine |
| `service_id` | int | — | Filtrer par service |
| `societe_id` | int | — | Filtrer par société |
| `filiale_id` | int | — | Filtrer par filiale |
| `role_id` | int | — | Filtrer par rôle |
| `page` | int | `1` | Numéro de page |
| `per_page` | int | `50` | Résultats par page (max : 200) |

#### Exemple de requête

```http
GET /api/v1/habilitations?statut_id=1&domaine_id=3&page=1&per_page=100
X-API-Key: lir_xxxx...
```

#### Exemple de réponse

```json
{
  "items": [
    {
      "id": 42,
      "nom_prenom": "Dupont Jean",
      "statut": "Actif",
      "statut_id": 1,
      "filiale": "Filiale Nord",
      "filiale_id": 2,
      "description": "Mission d'audit interne",
      "description_id": 5,
      "service": "Contrôle interne",
      "service_id": 3,
      "societe": "Meridia SA",
      "societe_id": 1,
      "role": "Auditeur",
      "role_id": 4,
      "domaine": "Finance",
      "domaine_id": 3,
      "date_octroi": "2024-01-15",
      "date_attestation": "2025-01-15",
      "attestation_expiree": false,
      "custom_fields": {
        "Région": "Île-de-France",
        "Niveau": "Expert"
      },
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-06-01T08:12:00"
    }
  ],
  "total": 87,
  "page": 1,
  "pages": 1,
  "per_page": 100
}
```

---

### `GET /api/v1/habilitations/{id}`

Retourne le détail complet d'une habilitation.

#### Paramètre de chemin

| Paramètre | Type | Description |
|-----------|------|-------------|
| `id` | int | Identifiant de l'habilitation |

#### Exemple de requête

```http
GET /api/v1/habilitations/42
X-API-Key: lir_xxxx...
```

#### Codes de retour

| Code | Signification |
|------|---------------|
| `200` | Habilitation trouvée — corps JSON |
| `404` | Habilitation introuvable |

---

### `GET /api/v1/referentiels`

Retourne l'ensemble des valeurs de référentiels (nécessaire pour résoudre les IDs dans les autres appels).

#### Exemple de requête

```http
GET /api/v1/referentiels
X-API-Key: lir_xxxx...
```

#### Exemple de réponse

```json
{
  "statuts": [
    { "id": 1, "label": "Actif",    "color": "green" },
    { "id": 2, "label": "Suspendu", "color": "yellow" },
    { "id": 3, "label": "Révoqué",  "color": "red" }
  ],
  "filiales":     [{ "id": 1, "label": "Filiale Nord" }],
  "descriptions": [{ "id": 1, "label": "Mission d'audit" }],
  "services":     [{ "id": 1, "label": "Contrôle interne" }],
  "societes":     [{ "id": 1, "label": "Meridia SA" }],
  "roles":        [{ "id": 1, "label": "Auditeur" }],
  "domaines":     [{ "id": 1, "label": "Finance" }],
  "custom": {
    "region": {
      "label": "Région",
      "values": [
        { "id": 1, "label": "Île-de-France" },
        { "id": 2, "label": "Grand Est" }
      ]
    }
  }
}
```

---

## Champ `attestation_expiree`

| Valeur | Signification |
|--------|---------------|
| `false` | Date d'attestation renseignée et non dépassée |
| `true` | Date d'attestation dépassée (habilitation en écart) |
| `null` | Pas de date d'attestation renseignée |

---

## Exemples d'intégration

### Python (httpx)

```python
import httpx

LIR_BASE = "http://localhost:8001/api/v1"
LIR_KEY  = "lir_xxxx..."

client = httpx.Client(headers={"X-API-Key": LIR_KEY}, base_url=LIR_BASE)

# 1. Charger les référentiels une fois (pour résoudre les IDs)
refs = client.get("/referentiels").json()
statut_actif_id = next(s["id"] for s in refs["statuts"] if s["label"] == "Actif")

# 2. Lister toutes les habilitations actives (toutes pages)
habs = []
page = 1
while True:
    data = client.get("/habilitations", params={
        "statut_id": statut_actif_id,
        "page": page,
        "per_page": 200,
    }).json()
    habs.extend(data["items"])
    if page >= data["pages"]:
        break
    page += 1

# 3. Filtrer les habilitations expirées
expirees = [h for h in habs if h["attestation_expiree"]]

# 4. Rechercher une personne
resultats = client.get("/habilitations", params={"q": "Dupont"}).json()["items"]
```

### Python (requests)

```python
import requests

session = requests.Session()
session.headers["X-API-Key"] = "lir_xxxx..."

habs = session.get("http://localhost:8001/api/v1/habilitations",
                   params={"domaine_id": 3}).json()["items"]
```

### JavaScript (fetch)

```js
const BASE = "http://localhost:8001/api/v1";
const KEY  = "lir_xxxx...";
const headers = { "X-API-Key": KEY };

const refs = await fetch(`${BASE}/referentiels`, { headers }).then(r => r.json());
const habs = await fetch(`${BASE}/habilitations?per_page=200`, { headers }).then(r => r.json());

console.log(habs.items.filter(h => h.attestation_expiree));
```

---

## Gestion des clés API

Accessible depuis l'interface BaseLIR : **Admin > API** (rôle Responsable requis).

| Action | Description |
|--------|-------------|
| Créer | Donner un nom identifiant l'application cliente (ex: `plandecontrole`) |
| Copier | La clé brute est affichée **une seule fois** — la conserver immédiatement |
| Révoquer | La clé devient inactive immédiatement, sans suppression de l'historique |
| Supprimer | Suppression définitive de la clé |

La colonne **Dernière utilisation** permet de détecter les clés inactives.

---

## Documentation interactive

L'interface Swagger UI, générée automatiquement par FastAPI, est disponible sur :

```
http://<hôte>:<port>/docs
```

Elle permet de tester tous les endpoints directement dans le navigateur (bouton **Authorize** pour saisir la clé API).

---

## Codes HTTP

| Code | Signification |
|------|---------------|
| `200` | Succès |
| `401` | Clé API manquante ou invalide |
| `404` | Ressource introuvable |
| `422` | Paramètre invalide (type incorrect, valeur hors limite) |
