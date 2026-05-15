# BaseLIR — Documentation API REST

API REST en lecture seule pour interroger la base des habilitations depuis une application externe.

---

## Authentification

Toutes les requêtes doivent inclure le header `X-API-Key` avec une clé générée depuis **Admin > API**.

```http
X-API-Key: lir_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Les clés sont stockées hachées (SHA-256) — le secret brut n'est affiché qu'à la création.

| Code | Signification |
|------|---------------|
| `401` | Clé absente, invalide ou révoquée |

---

## Base URL

```
http://<hôte>:<port>/api/v1
```

---

## Endpoints

### `GET /api/v1/habilitations`

Liste paginée d'habilitations avec filtres optionnels.

**Paramètres**

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `q` | string | — | Recherche partielle sur le nom/prénom (insensible à la casse) |
| `statut_id` | int | — | Filtrer par statut |
| `domaine_id` | int | — | Filtrer par domaine |
| `service_id` | int | — | Filtrer par service |
| `societe_id` | int | — | Filtrer par société |
| `filiale_id` | int | — | Filtrer par filiale |
| `role_id` | int | — | Filtrer par rôle |
| `page` | int | `1` | Numéro de page |
| `per_page` | int | `50` | Résultats par page (max : 200) |

Les IDs de référentiels sont obtenus via `GET /api/v1/referentiels`.

**Réponse**

```json
{
  "items": [ /* voir structure ci-dessous */ ],
  "total": 87,
  "page": 1,
  "pages": 2,
  "per_page": 50
}
```

---

### `GET /api/v1/habilitations/{id}`

Détail d'une habilitation.

| Code | Signification |
|------|---------------|
| `200` | OK |
| `404` | Habilitation introuvable |

---

### `GET /api/v1/referentiels`

Retourne toutes les valeurs de référentiels.

**Réponse**

```json
{
  "statuts":      [{ "id": 1, "label": "Actif",    "color": "green" }],
  "filiales":     [{ "id": 1, "label": "Filiale Nord" }],
  "descriptions": [{ "id": 1, "label": "Mission d'audit" }],
  "services":     [{ "id": 1, "label": "Contrôle interne" }],
  "societes":     [{ "id": 1, "label": "Meridia SA" }],
  "roles":        [{ "id": 1, "label": "Auditeur" }],
  "domaines":     [{ "id": 1, "label": "Finance" }],
  "custom": {
    "region": {
      "label": "Région",
      "values": [{ "id": 1, "label": "Île-de-France" }]
    }
  }
}
```

---

## Structure d'une habilitation

Retournée par les deux endpoints ci-dessus.

```json
{
  "id": 42,
  "nom_prenom": "Dupont Jean",
  "statut": "Actif",               "statut_id": 1,
  "filiale": "Filiale Nord",       "filiale_id": 2,
  "description": "Mission audit",  "description_id": 5,
  "service": "Contrôle interne",   "service_id": 3,
  "societe": "Meridia SA",         "societe_id": 1,
  "role": "Auditeur",              "role_id": 4,
  "domaine": "Finance",            "domaine_id": 3,
  "date_octroi": "2024-01-15",
  "date_attestation": "2025-01-15",
  "attestation_expiree": false,
  "date_sensibilisation": "2025-03-10",
  "sensibilisation_expiree": false,
  "custom_fields": { "Région": "Île-de-France" },
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-06-01T08:12:00"
}
```

**`attestation_expiree`**

| Valeur | Signification |
|--------|---------------|
| `false` | Date renseignée et non dépassée |
| `true` | Date dépassée — habilitation en écart |
| `null` | Pas de date d'attestation renseignée |

**`sensibilisation_expiree`**

| Valeur | Signification |
|--------|---------------|
| `false` | Sensibilisation SI renseignée et < 1 an |
| `true` | Dernière sensibilisation SI > 1 an — habilitation en écart |
| `null` | Pas de date de sensibilisation renseignée |

---

## Gestion des clés API

Dans **Admin > API** (rôle Responsable requis) :

| Action | Description |
|--------|-------------|
| Créer | Donner un nom à la clé (ex : `plandecontrole`) |
| Copier | La clé brute est affichée **une seule fois** |
| Révoquer | Désactive la clé immédiatement |
| Supprimer | Suppression définitive |

La colonne **Dernière utilisation** est mise à jour à chaque appel.

---

## Documentation interactive

Swagger UI disponible sur `http://<hôte>:<port>/docs` — cliquer sur **Authorize** pour saisir la clé.

---

## Codes HTTP

| Code | Signification |
|------|---------------|
| `200` | Succès |
| `401` | Clé API manquante ou invalide |
| `404` | Ressource introuvable |
| `422` | Paramètre invalide |
