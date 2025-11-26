# analysts_ui.py
from __future__ import annotations
from typing import List, Dict
import base64
import os
import uuid

import streamlit as st


def _img_to_b64(path: str) -> str | None:
    """Encode une image locale en base64, ou None si introuvable."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def build_from_config(config: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Transforme ANALYSTS_CONFIG en une liste prête à être affichée :
    - id unique
    - name, role
    - b64 : image encodée en base64
    """
    profiles: List[Dict[str, str]] = []

    for a in config:
        name = (a.get("name") or "Analyste").strip()
        role = (a.get("role") or "").strip()
        photo_path = (a.get("photo") or "").strip()

        b64 = _img_to_b64(photo_path)

        profiles.append(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "role": role,
                "b64": b64,
            }
        )

    return profiles


def render_profiles_panel() -> None:
    """
    Affiche la colonne de profils à droite :
    photo (classe .face) + nom + rôle.
    """
    profiles = st.session_state.get("profiles", [])

    if not profiles:
        st.info("Aucun profil à afficher.")
        return

    # CSS pour les noms / rôles (forcé en blanc pour le thème dark)
    st.markdown(
        """
        <style>
        .profile-card {
            text-align: center;
            margin-bottom: 1.2rem;
        }
        .profile-name {
            margin-top: 0.35rem;
            font-size: 0.85rem;
            font-weight: 600;
            color: #f9fafb !important; /* texte bien visible */
        }
        .profile-role {
            font-size: 0.70rem;
            color: #9ca3af !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for p in profiles:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)

        # Image
        if p.get("b64"):
            st.markdown(
                f'<img class="face" src="data:image/png;base64,{p["b64"]}" />',
                unsafe_allow_html=True,
            )

        # Nom
        st.markdown(
            f'<div class="profile-name">{p.get("name", "Analyste")}</div>',
            unsafe_allow_html=True,
        )

        # Rôle (optionnel)
        role = p.get("role", "").strip()
        if role:
            st.markdown(
                f'<div class="profile-role">{role}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
