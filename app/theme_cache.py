"""
Cache module-level du thème.
Chargé depuis la DB au démarrage, mis à jour quand l'admin change les couleurs.
Évite une requête DB à chaque rendu de template.
"""

_state: dict = {"primary": "teal", "secondary": "orange"}


def get() -> dict:
    return dict(_state)


def update(primary: str, secondary: str) -> None:
    _state["primary"] = primary
    _state["secondary"] = secondary


VALID_COLORS = {
    "teal", "blue", "indigo", "purple", "emerald",
    "rose", "sky", "slate", "orange", "amber", "pink", "violet",
}

# Hex 500 pour chaque palette (aperçu dans le sélecteur)
SWATCH_HEX = {
    "teal":    "#14b8a6",
    "blue":    "#3b82f6",
    "indigo":  "#6366f1",
    "purple":  "#a855f7",
    "emerald": "#10b981",
    "rose":    "#f43f5e",
    "sky":     "#0ea5e9",
    "slate":   "#64748b",
    "orange":  "#f97316",
    "amber":   "#f59e0b",
    "pink":    "#ec4899",
    "violet":  "#8b5cf6",
}

PRIMARY_CHOICES = ["teal", "blue", "indigo", "purple", "emerald", "rose", "sky", "slate"]
SECONDARY_CHOICES = ["orange", "amber", "pink", "violet", "teal", "sky", "rose", "emerald"]
