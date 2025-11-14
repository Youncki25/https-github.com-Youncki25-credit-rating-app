from __future__ import annotations
from typing import List, Dict, Optional
import base64, os, uuid

# ─────────────────────────────────────────────────────────
# CONFIGURATION — 10 analystes (modifiable par toi)
# Clés attendues par main.py (et par load_analysts ci-dessous) :
#   name : Nom affiché
#   role : Poste (apparaît en gras côté UI)
#   photo: Chemin de la photo (PNG/JPG). Laisse "" si pas d'image.
# ─────────────────────────────────────────────────────────
ANALYSTS_CONFIG: List[Dict[str, str]] = [
    {
        "name": "BELDJENNA",
        "role": "Senior Credit Analyst — US Market",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/Younes Beldjenna Analyste Senior .PNG",
    },
    {
        "name": "Matthew Er",
        "role": "Senior Credit Analyst — APAC Market",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/PHOTO-2025-10-12-12-37-24.jpg",
    },
    {
        "name": "Inès",
        "role": "Senior Credit Analyst - EMEA Market",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/IMG_1586.jpg",
    },
    {
        "name": "Marie-Gloriseuse Dupont",
        "role": "Senior Credit Analyst - LATAM Market",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/Capture d’écran . 2025-10-12 à 15.17.36.png",
    },
    {
        "name": "Sébastien Lecornue",
        "role": "FX & Macro Analyst",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/sebastien.jpeg",
    },
    {
        "name": "Emmanuel Macron",
        "role": "High Yield Analyst",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/manuel.jpeg",
    },
    {
        "name": "Gabriel Attal",
        "role": "Investment Grade Analyst",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/Gabriel.jpeg",
    },
    {
        "name": "François Bayrou",
        "role": "Quant Researcher",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/franois.webp",
    },
    {
        "name": "Aladeen Assad",
        "role": "Compliance Officer",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/Screenshot 2025-10-19 at 06.43.49.png",
    },
    {
        "name": "Michel Barnier",
        "role": "Structured Finance Analyst",
        "photo": "/Users/beldjenna/Desktop/Rating Algo/Photo/michel.jpeg",
    },
]

# ─────────────────────────────────────────────────────────
# Utilitaire optionnel (pour tester script.py tout seul)
# ─────────────────────────────────────────────────────────
def _img_to_b64(path: str) -> Optional[str]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def load_analysts() -> List[Dict]:
    """Charge et retourne la liste d'analystes avec leurs images encodées en base64."""
    analysts: List[Dict] = []
    for a in ANALYSTS_CONFIG:
        name = (a.get("name") or "Analyste").strip()
        role = (a.get("role") or "").strip()
        photo = (a.get("photo") or "").strip()

        b64 = _img_to_b64(photo)
        analysts.append(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "role": role,
                "b64": b64,
            }
        )
    return analysts


# ─────────────────────────────────────────────────────────
# Test console (facultatif). Si tu utilises main.py, ne lance pas ce fichier.
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    data = load_analysts()
    print(f"{len(data)} analystes chargés :")
    for a in data:
        print(f"- {a['name']} ({a['role']}) — photo {'OK' if a['b64'] else '❌'}")
