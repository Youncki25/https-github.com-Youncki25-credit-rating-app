#  streamlit run ui_streamlit.py
import os
from typing import Optional, List, Dict

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt  # si besoin pour d'autres graphes plus tard

from macro_graphs import render_macro_page

# Import depuis les modules utilitaires
from ratings_utils import (
    RATING_ORDER,
    RATING_TO_SCORE,
    MOODYS_TO_SP,
    score_to_rating,
    rating_to_ordinal,
    load_internal_ratings,
    internal_score_to_rating,
    INTERNAL_RATING_MAP_INV,
    external_rating_to_internal_score,
)

from analysts_ui import build_from_config, render_profiles_panel

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

.card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.9rem;
}

/* === 🔥 Photos carrées & plus grandes === */
.face {
    width: 100px !important;
    height: 100px !important;
    object-fit: cover;
    border-radius: 12px;      /* carré arrondi léger */
    display: block;
    margin-left: auto;
    margin-right: auto;       /* centre l’image */
    border: 2px solid #374151;
}

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
        ["Présentation", "Simulation de la note", "Macroéconomie", "Point économique", "Contact"],
        index=1,
    )
    st.sidebar.markdown("---")
    return page


# --------------------------------------------------------------------
# 📄 Contenu des pages
# --------------------------------------------------------------------
def _render_page_content(page: str):

    st.markdown("# 💹  AGENCE DE NOTATION MYMY'S")
    st.caption("Créé par Younes Beldjenna, Matthew Er, Ines Bouchafaa, Marie-Glorieuse....")
    st.markdown("---")

    # ------------------------------------------------------
    # Présentation
    # ------------------------------------------------------
    if page == "Présentation":
        st.markdown("### 👋 Bienvenue dans notre dashboard de notation souveraine")

        st.write(
            "Ce projet présente un modèle de notation souveraine que nous avons développé dans le cadre de notre Master 2. "
            "Le modèle s’appuie exclusivement sur des données macroéconomiques récupérées via API, notamment auprès du FMI "
            "et de la Banque Mondiale. Aucune donnée n’est issue de fichiers Excel statiques, ce qui rend l’outil "
            "entièrement réutilisable, actualisable et transparent dans le temps.\n\n"
            
            "Les notations des agences externes proviennent quant à elles de l’API Global Economics. Dans la section "
            "**Simulation de la note**, vous pourrez comparer les notes calculées par notre modèle interne avec celles "
            "publiées par les trois principales agences internationales.\n\n"

            "Nous avons estimé notre modèle sur un échantillon de **10 pays**, avant de l’appliquer à un nombre plus large "
            "de pays afin d’évaluer sa capacité prédictive. Certaines limites apparaissent cependant, notamment liées "
            "aux contraintes de stockage de la plateforme Streamlit : un nombre plus élevé de pays implique davantage "
            "de fichiers macroéconomiques, ce qui dépasse rapidement les quotas disponibles.\n\n"

            "Malgré ces contraintes, l’outil permet de proposer une démonstration complète, interactive et pédagogique de "
            "notre modèle de notation souveraine.\n\n"

            "Dans l’onglet **Macroéconomie**, vous trouverez également des visualisations des principaux indicateurs "
            "macroéconomiques pour les pays analysés. Les données proviennent de la World Bank, ce qui implique un certain "
            "décalage temporel par rapport à des bases de données premium comme Bloomberg.\n\n"

            "Nous publions aussi un **point macroéconomique hebdomadaire**, réalisé par nos équipes, afin d’offrir un suivi "
            "régulier de l’actualité économique internationale.\n\n"

            "Enfin, dans l’onglet **Modèle**, vous pourrez consulter notre document méthodologique détaillant notre démarche "
            "et la construction du modèle interne. L’onglet **Contact** vous permet de joindre directement nos équipes pour "
            "toute question ou demande d’information."
        )

    # ------------------------------------------------------
    # 📌 SIMULATION DE LA NOTE
    # ------------------------------------------------------
    elif page == "Simulation de la note":

        st.markdown("### Simulation de la note")
        st.write(
            "Vous trouverez ci-dessous les notations souveraines 2024 des trois principales "
            "agences ainsi que la note calculée par notre modèle interne."
        )

        # 🔹 Chargement + transformation du fichier Rating_API.xlsx (format long → large)
        try:
            ratings_raw = pd.read_excel("/Users/beldjenna/Desktop/Rating Algo/Rating_API.xlsx")
        except Exception as e:
            st.error(f"Erreur lors du chargement des notations 2024 (Rating_API.xlsx) : {e}")
            return

        # On garde uniquement l'année 2024
        if "Year" not in ratings_raw.columns:
            st.error("Le fichier Rating_API.xlsx doit contenir une colonne 'Year'.")
            return

        ratings_raw = ratings_raw[ratings_raw["Year"] == 2024].copy()

        # Vérifications minimales
        for col in ["Code", "Agency", "Rating", "Month"]:
            if col not in ratings_raw.columns:
                st.error(f"Le fichier Rating_API.xlsx doit contenir une colonne '{col}'.")
                return

        # Nettoyage
        ratings_raw["Code"] = ratings_raw["Code"].astype(str).str.strip()
        ratings_raw["Agency"] = ratings_raw["Agency"].astype(str).str.strip()
        ratings_raw["Rating"] = ratings_raw["Rating"].astype(str).str.strip()

        # On prend la dernière note par pays / agence (mois le plus récent)
        ratings_raw = ratings_raw.sort_values(["Code", "Agency", "Year", "Month"])
        last_obs = ratings_raw.groupby(["Code", "Agency"], as_index=False).tail(1)

        # Pivot : 1 ligne = 1 pays, 1 colonne par agence (S&P, Moody's, Fitch)
        ratings_2024 = last_obs.pivot(index="Code", columns="Agency", values="Rating")

        ratings_2024.columns = ratings_2024.columns.astype(str).str.strip()
        ratings_2024.index = ratings_2024.index.astype(str).str.strip()

        country_col = "Code"

        internal_ratings = load_internal_ratings()

        if ratings_2024 is None or ratings_2024.empty:
            st.warning("Aucune notation agence disponible dans Rating_API.xlsx pour l'année 2024.")
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

        # -----------------------------
        # 🔎 Liste des pays dans la selectbox
        #    → uniquement ceux qui ont une NOTE INTERNE
        # -----------------------------
        if internal_ratings is not None and "Code" in internal_ratings.columns:
            codes_internes = set(
                internal_ratings["Code"].dropna().astype(str).str.strip().unique()
            )
            index_ratings = set(ratings_2024.index.tolist())
            pays_dispos = sorted(index_ratings.intersection(codes_internes))

            if not pays_dispos:
                pays_options = sorted(ratings_2024.index.tolist())
            else:
                pays_options = pays_dispos
        else:
            pays_options = sorted(ratings_2024.index.tolist())

        pays = st.selectbox("Pays", pays_options)

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

                if pd.isna(letter):
                    st.markdown(
                        f"💡 <b>Note {agence} 2024 pour {pays} :</b> "
                        f"<span style='font-size:22px;font-weight:bold'>N/A</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    # Conversion vers l'échelle interne (score numérique)
                    internal_score = external_rating_to_internal_score(letter, agence)

                    if internal_score is None:
                        score_str = "N/A"
                    else:
                        score_str = str(internal_score)

                    st.markdown(
                        f"💡 <b>Note {agence} 2024 pour {pays} :</b> "
                        f"<span style='font-size:22px;font-weight:bold'>{letter} ({score_str})</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.warning(f"Colonne {agence} manquante dans Rating_API.xlsx.")

        # ---- ÉCHELLE INTERNE (modèle) ----
        else:
            if internal_ratings is None:
                st.warning(
                    "Les notes internes ne sont pas encore disponibles "
                    "(fichier internal_ratings_*.xlsx manquant)."
                )
            else:
                if "Code" not in internal_ratings.columns:
                    st.error("Le fichier internal_ratings_*.xlsx doit contenir une colonne 'Code'.")
                elif "predicted_cat" not in internal_ratings.columns:
                    st.error("Le fichier internal_ratings_*.xlsx doit contenir une colonne 'predicted_cat'.")
                elif "expected_score" not in internal_ratings.columns:
                    st.error("Le fichier internal_ratings_*.xlsx doit contenir une colonne 'expected_score'.")
                else:
                    internal_ratings["Code"] = (
                        internal_ratings["Code"].astype(str).str.strip()
                    )
                    row = internal_ratings[internal_ratings["Code"] == pays]
                    if row.empty:
                        st.warning(f"Aucune note interne disponible pour {pays}.")
                    else:
                        cat = int(row["predicted_cat"].iloc[0])
                        expected = float(row["expected_score"].iloc[0])
                        letter = internal_score_to_rating(cat)

                        st.markdown(
                            f"💡 <b>Note interne 2024 pour {pays} :</b> "
                            f"<span style='font-size:24px;font-weight:bold'>{letter} ({cat})</span>",
                            unsafe_allow_html=True,
                        )

                        st.caption(
                            f"Score continu estimé : {expected:.2f} • "
                            f"Catégorie interne : {cat} • Équivalent lettre : {letter}"
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
    # POINT ÉCONOMIQUE
    # ------------------------------------------------------
    elif page == "Point économique":
        st.markdown("## 📅 Agenda économique de la semaine")
        st.markdown(
            "Principaux événements macroéconomiques de la semaine, inspirés du "
            "[calendrier économique d’Investing.com](https://www.investing.com/economic-calendar/)."
        )

        st.markdown("---")

        # 🔹 Mardi
        st.markdown("### 📌 Mardi")
        st.write(
            "- 🇺🇸 **Confiance des consommateurs (US)** – indicateur clé du moral des ménages "
            "et de la dynamique de la demande."
        )

        # 🔹 Mercredi
        st.markdown("### 📌 Mercredi")
        st.write("- 🇦🇺 **CPI Australie** – inflation importante pour la RBA.")
        st.write("- 🇳🇿 **Décision de taux RBNZ**.")
        st.write("- 🇺🇸 **PIB US (2e estimation)**.")
        st.write("- 🇺🇸 **PCE core & headline** – inflation préférée de la Fed.")

        # 🔹 Jeudi
        st.markdown("### 📌 Jeudi")
        st.write("- 🇺🇸 **Thanksgiving (US)** – marchés américains quasi fermés.")
        st.write("- 🇯🇵 **Inflation Tokyo** – indicateur avancé.")

        # 🔹 Vendredi
        st.markdown("### 📌 Vendredi")
        st.write("- 🇩🇪 **Ventes au détail Allemagne**.")
        st.write("- 🇨🇭 **PIB Suisse**.")
        st.write("- 🇩🇪 **Inflation préliminaire Allemagne**.")
        st.write("- 🇨🇦 **PIB Canada**.")

        # 🔹 Week-end
        st.markdown("### 📌 Week-end")
        st.write("- 🇨🇳 **PMI manufacturier & non manufacturier Chine**.")

        st.markdown("---")
        st.caption(
            "⚠️ Les dates exactes peuvent varier — toujours vérifier le calendrier Investing en temps réel."
        )

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


# Permet le run direct : streamlit run ui_streamlit.py
if __name__ == "__main__":
    launch_dashboard()
