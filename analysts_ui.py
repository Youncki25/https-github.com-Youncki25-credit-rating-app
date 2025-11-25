# analysts_ui.py
import os
import uuid
import base64
from dataclasses import dataclass
from typing import Optional, List, Dict

import streamlit as st


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


def build_from_config(config: List[Dict]) -> List[Analyst]:
    """Construit la liste d'analystes à partir de ANALYSTS_CONFIG."""
    out: List[Analyst] = []
    for a in config:
        out.append(
            Analyst(
                id=str(uuid.uuid4()),
                name=a.get("name", "Analyste"),
                role=a.get("role", ""),
                b64=_img_to_b64(a.get("photo", "")),
                validated=False,
            )
        )
    return out


def render_profiles_panel():
    """Affiche le panneau de droite avec les profils d'analystes (sans actions)."""
    st.markdown("### Profils")

    if "profiles" not in st.session_state:
        st.session_state.profiles = []

    if not st.session_state.profiles:
        st.caption("Aucun profil configuré dans script.py.")
    else:
        for prof in st.session_state.profiles:
            c1, c2 = st.columns([1, 3])
            with c1:
                if prof.b64:
                    st.markdown(
                        f"<img class='face' src='data:image/png;base64,{prof.b64}'/>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div class='card small'>Image manquante</div>",
                        unsafe_allow_html=True,
                    )
                    with c2:
                        st.markdown(
                        f"<b>{prof.name}</b><br/>{prof.role}",
                    unsafe_allow_html=True,
                                                )

