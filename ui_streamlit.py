# ui_streamlit.py
import os
from typing import Optional, List, Dict

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt  # si tu en as besoin plus tard

from macro_graphs import render_macro_page

# Import depuis tes nouveaux modules
from ratings_utils import (
    RATING_ORDER,
    RATING_TO_SCORE,
    MOODYS_TO_SP,
    score_to_rating,
    rating_to_ordinal,
    load_ratings_2024,
    load_internal_ratings,
)
from analysts_ui import Analyst, build_from_config, render_profiles_panel

try:
    from script import ANALYSTS_CONFIG  # [{name, role, photo}, ...]
except Exception:
    st.error(
        "❌ Impossible d'importer ANALYSTS_CONFIG depuis script.py. "
        "Vérifie le fichier et son emplacement."
    )
    st.stop()


# ----------------------------------
# 🌙 Thème sombre / CSS
# ----------------------------------
DARK_CSS = """
<style>
:root { --bg:#000; --panel:#0d0d0d; --text:#e5e7eb; --muted:#9ca3af; --line:#1f2937; }
.stApp { background: var(--bg); color: var(--text); font-family: ui-monospace; }
h1, h2, h3, h4 { color: var(--text); }
hr { border: none; border-top: 1px solid var(--line); margin: 0.75rem 0; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 0.9rem; }
.face { width:72px; height:72px; border-radius: 50%; object-fit: cover; border: 1px solid #374151; }
.small { font-size: 12px; color: var(--muted); }
</style>
"""


# --------------------------------------------------------------------
# 🧭 Sidebar / Navigation
# --------------------------------------------------------------------
def _render_sidebar() -> str:
    st.sidebar.markdown("### Menu")
    page = st.sidebar.radio(
        "Navigation",
        ["Présentation", "Simulation de la note", "Macroéconomie", "Contact"],
        index=0,
    )
    st.sidebar.markdown("---")
    return page


# --------------------------------------------------------------------
# 📄 Contenu des pages
# --------------------------------------------------------------------
def _render_page_content(page: str):

    st.markdown("# 💹  Calculateur de Note")
    st.caption("Déterminez la note de crédit souveraine selon agences & modèle interne.")
    st.markdown("---")

    # ------------------------------------------------------
    # Présentation
    # ------------------------------------------------------
    if page == "Présentation":
        st.markdown("### Explication du projet")
        st.write(
            "Nous avons construit un modèle de notation souveraine basé sur des données "
            "macroéconomiques récupérées via API. Aucune donnée ne provient d’un fichier "
            "Excel figé : l’outil est donc réutilisable dans le temps."
        )
        st.markdown("[Voir documentation du modèle](https://ton-lien-ici.com)")

    # ------------------------------------------------------
    # 📌 SIMULATION DE LA NOTE
    # ------------------------------------------------------
    elif page == "Simulation de la note":

        st.markdown("### Simulation de la note")
        st.write(
            "Vous trouverez ci-dessous les notations souveraines 2024 des trois principales "
            "agences ainsi que la note calculée par notre modèle interne."
        )

        ratings_2024, country_col = load_ratings_2024()
        internal_ratings = load_internal_ratings()

        if ratings_2024 is None:
            st.warning("Aucune notation agence disponible.")
            return

        st.markdown('<div class="card">', unsafe_allow_html=True)

        methodology = st.selectbox(
            "Méthodologie",
            [
                "Échelle S&P (AAA–D)",
                "Échelle Moody's (Aaa–C)",
                "Échelle Fitch (AAA–D)",
                "Échelle interne",
            ],
        )

        pays = st.selectbox("Pays", ratings_2024.index.tolist())

        methodology_to_agency = {
            "Échelle S&P (AAA–D)": "S&P",
            "Échelle Moody's (Aaa–C)": "Moody's",
            "Échelle Fitch (AAA–D)": "Fitch",
            "Échelle interne": None,
        }

        agence = methodology_to_agency[methodology]

        # ---- AGENCES EXTERNES ----
        if agence:
            if agence in ratings_2024.columns:
                letter = ratings_2024.loc[pays, agence]
                score = rating_to_ordinal(letter)

                st.markdown(
                    f"💡 <b>Note {agence} 2024 pour {pays} :</b> "
                    f"<span style='font-size:22px;font-weight:bold'>{letter} ({score})</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.warning(f"Colonne {agence} manquante dans rating2.xlsx.")

        # ---- ÉCHELLE INTERNE ----
        else:
            if internal_ratings is None:
                st.warning("Aucune note interne trouvée.")
            else:
                row = internal_ratings[internal_ratings["Code"] == pays]
                if row.empty:
                    st.warning(f"Aucune note interne disponible pour {pays}.")
                else:
                    cat = int(row["predicted_cat"].iloc[0])
                    expected = float(row["expected_score"].iloc[0])
                    letter = score_to_rating(cat)

                    st.markdown(
                        f"💡 <b>Note interne 2024 pour {pays} :</b> "
                        f"<span style='font-size:24px;font-weight:bold'>{letter} ({cat})</span>",
                        unsafe_allow_html=True,
                    )

                    st.caption(
                        f"Score continu estimé : {expected:.2f} • "
                        f"Catégorie : {cat} • Équivalent lettre : {letter}"
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------------
    # MACRO
    # ------------------------------------------------------
    elif page == "Macroéconomie":
        st.markdown("## Données macroéconomiques")
        st.write("Visualisation des indicateurs macro pour chaque pays.")
        render_macro_page()

    # ------------------------------------------------------
    # CONTACT
    # ------------------------------------------------------
    elif page == "Contact":
        st.markdown("### Contact")
        st.write("Ajoutez ici les emails, liens, etc.")


# --------------------------------------------------------------------
# 🚀 Lancement dashboard
# --------------------------------------------------------------------
def launch_dashboard():
    # CSS global
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    # Navigation
    page = _render_sidebar()

    # Initialisation des profils si nécessaire
    if "profiles" not in st.session_state:
        st.session_state.profiles = build_from_config(ANALYSTS_CONFIG)

    # Layout 2 colonnes : contenu à gauche, profils à droite
    left, right = st.columns([5, 2])
    with left:
        _render_page_content(page)
    with right:
        render_profiles_panel()


# Optionnel : permettre le run direct par `streamlit run ui_streamlit.py`
if __name__ == "__main__":
    launch_dashboard()
