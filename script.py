from __future__ import annotations
from typing import List, Dict, Optional
import base64, os, uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ANALYSTS_CONFIG: List[Dict[str, str]] = [
    {
        "name": "Younes Beldjenna",
        "role": "Senior Credit Analyst — US Market",
        "photo": "Photo/Younes Beldjenna Analyste Senior.jpg",
    },
    {
        "name": "Matthew Er",
        "role": "Senior Credit Analyst — APAC Market",
        "photo": "Photo/matthew Er.jpg",
    },
    {
        "name": "Inès Bouchafaa",
        "role": "Senior Credit Analyst - EMEA Market",
        "photo": "Photo/Ines.jpg",
    },
    {
        "name": "Marie-Gloriseuse Ndjoli bofambi",
        "role": "Senior Credit Analyst - LATAM Market",
        "photo": "Photo/marie.jpg",
    },
    {
        "name": "Sébastien Lecornu",
        "role": "FX & Macro Analyst",
        "photo": "Photo/sebastien",   # pas d’extension dans ton dossier
    },
    {
        "name": "Emmanuel Macron",
        "role": "High Yield Analyst",
        "photo": "Photo/manuel",      # pas d’extension
    },
    {
        "name": "Gabriel Attal",
        "role": "Investment Grade Analyst",
        "photo": "Photo/Gabriel",     # pas d’extension
    },
    {
        "name": "François Bayrou",
        "role": "Quant Researcher",
        "photo": "Photo/franois.webp",  # comme sur ta capture (sans c)
    },
    {
        "name": "Michel Barnier",
        "role": "Structured Finance Analyst",
        "photo": "Photo/michel",      # pas d’extension
    },
]

def _img_to_b64(path: str) -> Optional[str]:
    if not path:
        return None

    full_path = os.path.join(BASE_DIR, path)
    if not os.path.exists(full_path):
        print("❌ Image introuvable :", full_path)
        return None

    try:
        with open(full_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        print("⚠️ Erreur lecture image :", full_path, "—", e)
        return None


def load_analysts() -> List[Dict]:
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


if __name__ == "__main__":
    data = load_analysts()
    print(f"{len(data)} analystes chargés :")
    for a in data:
        print(f"- {a['name']} ({a['role']}) — photo {'OK' if a['b64'] else '❌'}")
