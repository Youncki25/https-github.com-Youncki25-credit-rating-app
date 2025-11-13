# ui : interface du streallit 
# ui_streamlit.py
import streamlit as st
from dataclasses import dataclass
from typing import Optional, List, Dict
import base64, os, uuid
import pandas as pd
import matplotlib.pyplot as plt
from macro_graphs import render_macro_page


try:
    from script import ANALYSTS_CONFIG  # [{name, role, photo}, ...]
except Exception:
    st.error(
        "❌ Impossible d'importer ANALYSTS_CONFIG depuis script.py. "
        "Vérifie le fichier et son emplacement."
    )
    st.stop()

# --------- Thème sombre / CSS ----------
DARK_CSS = """
<style>
:root { --bg:#000; --panel:#0d0d0d; --text:#e5e7eb; --muted:#9ca3af; --line:#1f2937; }
.stApp { background: var(--bg); color: var(--text); font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
h1, h2, h3, h4 { color: var(--text); }
hr { border: none; border-top: 1px solid var(--line); margin: 0.75rem 0; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 0.9rem; }
.face { width:72px; height:72px; border-radius: 50%; object-fit: cover; border: 1px solid #374151; }
.small { font-size: 12px; color: var(--muted); }
.badge { display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid var(--line); color:#10b981; font-size:12px; }
</style>
"""

@dataclass
class Analyst:
    id: str
    name: str
    role: str
    b64: Optional[str] = None
    validated: bool = False


def _img_to_b64(path: str) -> Optional[str]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def _build_from_config(config: List[Dict]) -> List[Analyst]:
    out: List[Analyst] = []
    for a in config:
        name = str(a.get("name", "Analyste")).strip() or "Analyste"
        role = str(a.get("role", "")).strip()
        photo = str(a.get("photo", "")).strip()
        out.append(
            Analyst(
                id=str(uuid.uuid4()),
                name=name,
                role=role,
                b64=_img_to_b64(photo),
                validated=False,
            )
        )
    return out

# --------- Sous-vues UI ----------
def _render_sidebar() -> str:
    st.sidebar.markdown("### Menu")
    page = st.sidebar.radio(
    "Navigation",
    ["Présentation", "Simulation de la note", "Macroéconomie", "Contact"],
    index=0,
    )
    st.sidebar.markdown("---")
    return page

def _render_profiles_panel():
    """Colonne droite : liste des profils + actions (Valider / Supprimer / Reset)."""
    st.markdown("### Profils")
    if not st.session_state.profiles:
        st.caption("Aucun profil. Clique sur **Reset** pour recharger depuis script.py.")
    else:
        for prof in st.session_state.profiles:
            # 1 seule ligne de colonnes (pas d'imbrication >1)
            c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
            with c1:
                if prof.b64:
                    st.markdown(
                        f"<img class='face' src='data:image/png;base64,{prof.b64}' alt='{prof.name}' />",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("<div class='card small'>Image introuvable</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{prof.name}**<br/>**{prof.role}**", unsafe_allow_html=True)
            with c3:
                prof.validated = st.checkbox("Valider", value=prof.validated, key=f"val_{prof.id}")
            with c4:
                if st.button("Supprimer", key=f"del_{prof.id}"):
                    st.session_state.profiles = [p for p in st.session_state.profiles if p.id != prof.id]
                    st.experimental_rerun()

    st.markdown("---")
    if st.button("🔄 Reset depuis script.py"):
        st.session_state.profiles = _build_from_config(ANALYSTS_CONFIG)
        st.experimental_rerun()

def _render_page_content(page: str):
    st.markdown("# 💹  Agence de Notation MIMY")
    st.caption("Agence de notation transparente et innovante.")
    st.markdown("---")



    if page == "Présentation":
        st.markdown("### Data")
        st.write(
            "Bonjour, Nous sommes ravie de vous avoir comme client nous somme la premiere agence de notation "
            "qui note ses clients de manière transparentes. Vous trouverez ci-joint notre modèles de rating et "
            "les données qui sont utiliser. Vous trouverez également une note des analystes senior accompagné "
            "de l'étude de l'analyste junior."
        )
        st.markdown("[📄 Voir le modèle de rating](https://ton-lien-ici.com)")
        st.markdown("<br/><span class='badge'>LIVE</span>", unsafe_allow_html=True)

    elif page == "Simulation de la note":
        st.markdown("### Simulation de la note")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        issuer = st.text_input("Nom de l'émetteur")
        methodology = st.selectbox(
            "Méthodologie",
            ["Échelle S&P (AAA–D)", "Échelle Moody's (Aaa–C)", "Échelle Fitch (AAA–D)", "Échelle interne"],
        )

    elif page == "Macroéconomie":
        render_macro_page()



    elif page == "Contact":
        st.markdown("### Contact")
        st.write("Ajoute ici des liens, emails ou formulaires de contact (Streamlit forms).")
        st.markdown("- Email : contact@tonagence.com\n- Téléphone : +33 1 23 45 67 89")

# --------- Point d’entrée UI ----------
def launch_dashboard():
    # Injecte le CSS
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    # Sidebar (choix de page)
    page = _render_sidebar()

    # État en session (profils)
    if "profiles" not in st.session_state:
        st.session_state.profiles = _build_from_config(ANALYSTS_CONFIG)

    # Layout principal : gauche (contenu) / droite (profils)
    left, right = st.columns([5, 2])
    with left:
        _render_page_content(page)
    with right:
        _render_profiles_panel()
