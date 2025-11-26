from __future__ import annotations
from typing import List, Dict, Optional
import base64, os, uuid


ANALYSTS_CONFIG: List[Dict[str, str]] = [
    {
        "name": " Younes Beldjenna",
        "role": "Senior Credit Analyst — US Market",
        "photo": "Photo/Younes Beldjenna Analyste Senior .PNG",
    },
    {
        "name": "Matthew Er",
        "role": "Senior Credit Analyst — APAC Market",
        "photo": "Photo/matthew Er .jpg",
    },
    {
        "name": "Inès Bouchafaa",
        "role": "Senior Credit Analyst - EMEA Market",
        "photo": "Photo/Ines.jpg",
    },
    {
        "name": "Marie-Gloriseuse Ndjoli bofambi",
        "role": "Senior Credit Analyst - LATAM Market",
        "photo": "Photo/marie.png",
    },
    {
        "name": "Sébastien Lecornu",
        "role": "FX & Macro Analyst",
        "photo": "Photo/sebastien.jpeg",
    },
    {
        "name": "Emmanuel Macron",
        "role": "High Yield Analyst",
        "photo": "Photo/manuel.jpeg"
    },
    {
        "name": "Gabriel Attal",
        "role": "Investment Grade Analyst",
        "photo": "Photo/Gabriel.jpeg",
    },
    {
        "name": "François Bayrou",
        "role": "Quant Researcher",
        "photo": "Photo/franois.webp",
    },
    {
        "name": "Michel Barnier",
        "role": "Structured Finance Analyst",
        "photo": "Photo/michel.jpeg",
    },
]

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
