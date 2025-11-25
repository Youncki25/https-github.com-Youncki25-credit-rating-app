#  streamlit run ui_streamlit.py
import os
from typing import Optional, List, Dict

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt  # si besoin pour d'autres graphes plus tard
 import base64
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
# 📂 Chemin du fichier Rating_API.xlsx (relatif au script)
# ----------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RATING_API_PATH = os.path.join(BASE_DIR, "Rating_API.xlsx")


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
        ["Présentation", "Simulation de la note", "Macroéconomie", "Calendrier", "Contact"],
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



    pdf_path = "/Users/beldjenna/Desktop/Rating Algo/Rating__project-2.pdf"

    def display_pdf(file_path):
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode("utf-8")
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="900px" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)

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
        st.markdown("## 📄 Document de méthodologie")
        st.write("Voici notre document PDF utilisé dans le projet :")
        display_pdf(pdf_path)


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
            ratings_raw = pd.read_excel(RATING_API_PATH)
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

        # -----------------------------
        # 📝 Récap analystes (textes pour certains pays)
        # -----------------------------
        analyst_notes = {
            "ECU": """L’Équateur reste confronté à un environnement macroéconomique tendu, malgré sa dollarisation qui stabilise l’inflation. La croissance est modeste, autour de 1–2 %, freinée par l’incertitude politique, la faiblesse de l’investissement et l’augmentation de l’insécurité intérieure. L’inflation demeure très faible (≈ 2 %), ce qui est typique des économies dollarisées, mais cela ne suffit pas à compenser les pressions structurelles sur l’activité.

Sur le plan budgétaire, la situation reste fragile : le déficit public tourne autour de 3–4 % du PIB, et la dette dépasse 60 % du PIB, dans un contexte d’accès limité aux marchés internationaux. Le gouvernement dépend largement de financements multilatéraux (FMI, BID) et de recettes liées au pétrole, un secteur sous pression après plusieurs décisions de réduction ou suspension d’extraction. L’absence de politique monétaire autonome — due à la dollarisation — rend l’ajustement économique entièrement dépendant de la discipline budgétaire et des réformes structurelles.

Globalement, l’Équateur présente une inflation faible mais une croissance atone, une situation budgétaire délicate et une exposition élevée aux risques politiques et pétroliers, ce qui pèse sur la stabilité macroéconomique et la notation souveraine.""",
            "EGY": """L’Égypte traverse une période économique très délicate, marquée par une forte inflation, une pénurie de devises et plusieurs dévaluations successives de la livre depuis 2022. La croissance s’est nettement affaiblie, désormais proche de 3 %, sous l’effet du recul de la consommation et de tensions persistantes sur les importations. L’inflation reste extrêmement élevée — longtemps au-dessus de 30 % — même si elle montre récemment des signes de modération grâce au resserrement monétaire et au ralentissement de la demande.

La Banque centrale maintient une politique très restrictive, avec un taux directeur à 27,25 %, l’un des plus élevés du monde, afin de stabiliser la monnaie et d’éviter une nouvelle spirale inflationniste. Sur le plan budgétaire, la situation demeure fragile : le déficit dépasse 6 % du PIB, la dette publique est élevée (près de 95 % du PIB) et la charge d’intérêt absorbe une part croissante du budget. Le pays dépend fortement des financements extérieurs, notamment du FMI, du Golfe et des euro-obligations, pour stabiliser sa balance des paiements.

Globalement, l’Égypte reste en situation de stabilisation sous contrainte, avec un ajustement monétaire et budgétaire sévère mais indispensable pour restaurer la confiance et réduire les déséquilibres macro-financiers.""",
            "VNM": """L’économie vietnamienne reste l’une des plus dynamiques d’Asie du Sud-Est, avec une croissance autour de 5–6 %, tirée par les exportations, la fabrication électronique et l’investissement direct étranger. Le pays bénéficie encore du mouvement de relocalisation industrielle hors de Chine, même si le ralentissement américain et européen pèse temporairement sur les ventes extérieures. L’inflation demeure maîtrisée, évoluant autour de 3–3,5 %, ce qui permet à la Banque d’État du Vietnam de maintenir une politique monétaire relativement accommodante pour soutenir l’activité.

Sur le plan budgétaire, la situation reste globalement stable : le déficit tourne autour de 3–4 % du PIB, et la dette publique, proche de 40 % du PIB, reste modérée pour un émergent. Le gouvernement continue de renforcer l’investissement dans les infrastructures et de simplifier l’environnement réglementaire pour attirer davantage de capitaux étrangers. Globalement, le Vietnam combine une croissance robuste, une inflation contenue et une trajectoire budgétaire maîtrisée, même si l’économie reste sensible au cycle mondial et à la demande extérieure.""",
            "GBR": """L’économie britannique reste fragile après plusieurs années de chocs successifs : Brexit, inflation importée, tensions sur l’énergie et resserrement monétaire rapide. La croissance demeure très faible, autour de 0,5–1 %, avec une demande intérieure encore contrainte par la baisse du pouvoir d’achat et un marché immobilier en net ralentissement. L’inflation, qui avait dépassé 11 % en 2022, a fortement reflué mais reste proche de 3–3,5 %, au-dessus de la cible de la Banque d’Angleterre.

La BoE maintient des taux élevés, avec un Bank Rate à 5,25 %, et ne prévoit un assouplissement que lorsque l’inflation convergera plus clairement vers 2 %. Sur le plan budgétaire, le Royaume-Uni affiche un déficit encore conséquent, proche de 4–5 % du PIB, et une dette publique supérieure à 100 % du PIB, ce qui limite les marges de manœuvre fiscales du gouvernement.

L’environnement économique reste donc complexe : croissance faible, inflation encore trop élevée, et paysage politique incertain, même si la désinflation progressive crée les conditions d’un possible assouplissement monétaire en 2025.""",
            "JAP": """L’économie japonaise évolue dans un contexte de croissance modeste mais stable, autour de 1 %, freinée par la faiblesse de la consommation et les tensions persistantes sur le marché du travail. L’inflation, longtemps trop basse, s’est installée durablement au-dessus de 2 %, ce qui marque un changement structurel après des décennies de déflation. La Banque du Japon a commencé sa normalisation graduelle : après avoir abandonné le contrôle de la courbe des taux, elle maintient désormais un taux directeur légèrement positif, autour de 0–0,25 %, tout en signalant que tout resserrement supplémentaire sera très progressif afin de ne pas fragiliser l’activité.

Sur le plan budgétaire, la situation reste délicate : la dette publique dépasse 250 % du PIB, la plus élevée du monde développé, et les pressions de dépense augmentent (vieillissement, santé, retraites). Malgré cette dette massive, le Japon bénéficie encore de coûts d’emprunt très faibles grâce au rôle stabilisateur de la BoJ et à une forte détention domestique de la dette. Globalement, le pays avance lentement vers une normalisation monétaire, mais reste confronté à un potentiel de croissance faible et à une situation budgétaire structurellement tendue.""",
            "GRE": """La Grèce poursuit sa normalisation économique après une décennie de crise. La croissance reste solide pour un pays de la zone euro, autour de 2–2,5 %, portée par le tourisme, les investissements européens et une amélioration progressive du climat financier. L’inflation a nettement reculé, se situant autour de 3 %, ce qui a permis un allègement des pressions sur les ménages et les entreprises. Sur le plan budgétaire, la Grèce affiche désormais un excédent primaire, tandis que la dette publique — encore très élevée en niveau — suit une trajectoire clairement descendante grâce à une forte croissance nominale et des taux d’emprunt modérés.

La politique monétaire dépend de la BCE : les taux directeurs de la zone euro ont commencé à reculer en 2024–2025, réduisant progressivement le coût du financement pour Athènes. Grâce à cette amélioration macroéconomique et budgétaire, la Grèce bénéficie d’une meilleure perception des marchés et a récupéré sa notation « investment grade » chez plusieurs agences. Malgré tout, le pays reste sensible à la conjoncture européenne et au ralentissement de la demande extérieure.""",
            "ZAF": """L’Afrique du Sud reste confrontée à une croissance très faible, limitée autour de 0,5–1 %, en raison des contraintes structurelles persistantes dans l’énergie (load-shedding), les transports et la sécurité. L’inflation a nettement ralenti mais évolue encore autour de 5 %, soit près de la borne haute de la cible de la Banque centrale. Dans ce contexte, la SARB maintient un taux directeur élevé à 8,25 %, ce qui implique un prime lending rate de 11,75 %, l’un des plus hauts parmi les grands émergents, reflétant une politique monétaire délibérément restrictive.

Sur le plan budgétaire, le déficit demeure élevé (≈ 4–5 % du PIB) et la dette publique dépasse 70 % du PIB, aggravée par les difficultés financières des entreprises publiques comme Eskom et Transnet. Malgré ces déséquilibres, le cadre macroéconomique reste relativement stable, mais la faiblesse chronique de la croissance et les risques budgétaires continuent de peser lourdement sur la trajectoire économique et la notation souveraine du pays.""",
            "ARG": """L’Argentine traverse toujours une phase d’ajustement macroéconomique extrêmement profonde sous la présidence de Javier Milei. Après l’hyperinflation de 2023–2024, les prix ont commencé à décélérer mais restent à un niveau exceptionnellement élevé, autour de 80–100 % en glissement annuel, maintenant l’économie dans un état permanent de tension sociale et de perte de pouvoir d’achat. L’activité a plongé au premier semestre 2025 sous l’effet du choc fiscal et monétaire, avec une contraction du PIB proche de –3 %, même si certains indicateurs avancés suggèrent un début de stabilisation.

Sur le plan budgétaire, le gouvernement poursuit une politique de déficit primaire proche de zéro, via un ajustement brutal des dépenses publiques, la suppression de subventions énergétiques et une réduction massive des transferts aux provinces. La consolidation est réelle mais au prix d’un fort coût social. La dette reste tendue, notamment en devises, et le pays reste exclu des marchés internationaux.

La politique monétaire reste ultra-restrictive : les taux directeurs demeurent très élevés en termes réels malgré plusieurs révisions techniques du régime monétaire. La Banque centrale cherche à restaurer la crédibilité après des années de financement monétaire du déficit. Le gouvernement maintient un plan de transition vers la dollarisation, même si la mise en œuvre est progressive et dépend d’une stabilisation durable des réserves.

En résumé, l’Argentine est engagée dans une stabilisation douloureuse : l’inflation baisse mais reste extrême, la croissance est négative, l’ajustement budgétaire est massif et la visibilité reste faible faute d’accès aux marchés.""",
            "USA": """L’économie américaine reste résiliente, avec une croissance supérieure à celle des autres pays développés, même si la dynamique ralentit légèrement. L’inflation poursuit son mouvement de désinflation mais reste bloquée autour de 3 %, un niveau trop élevé pour permettre une normalisation rapide. Le paysage économique est actuellement brouillé par le shutdown partiel du gouvernement fédéral, qui a déjà entraîné le report de plusieurs statistiques clés, compliquant l’évaluation de la conjoncture. Sur le plan budgétaire, le déficit demeure massif (≈ 6 % du PIB) et la charge d’intérêt continue de peser lourdement dans un contexte de dette record.

Côté Fed, les marchés anticipaient encore récemment une troisième baisse de taux en décembre, qui aurait fait passer le corridor des Fed Funds de 3,75–4,00 % à 3,50–3,75 %. Mais la probabilité de cette baisse a nettement reculé ces dernières semaines : plusieurs membres du FOMC ont jugé que l’inflation était trop persistante pour assouplir davantage la politique monétaire immédiatement. Le comité semble désormais s’orienter vers une pause, dans l’attente d’une nouvelle série de données fiables une fois le shutdown levé."""
        }

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

        # ------------------------------------------------------------------
        # 📝 Affichage du récap analystes
        #    → seulement si Échelle interne + pays dans le dictionnaire
        # ------------------------------------------------------------------
        if methodology == "Échelle interne":
            code_pays = str(pays).strip()
            recap = analyst_notes.get(code_pays)
            if recap:
                st.markdown("#### 📝 Analyse des analystes")
                st.write(recap)

        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------------
    # MACRO
    # ------------------------------------------------------
    elif page == "Macroéconomie":
        st.markdown("## Données macroéconomiques")
        st.write("Visualisation des indicateurs macro pour chaque pays.")
        render_macro_page()

    # ------------------------------------------------------
    # CALENDRIER ÉCONOMIQUE
    # ------------------------------------------------------
    elif page == "Calendrier":
        st.markdown("## 📅 Agenda économique de la semaine")
        st.markdown(
            "Principaux événements macroéconomiques de la semaine, inspirés du "
            "[calendrier économique d’Investing.com](https://www.investing.com/economic-calendar/)."
        )

        st.markdown("---")

        # 🔹 Mardi
        st.markdown("### 📌 Mardi 25 Novembre")
        st.write(
            "- 🇺🇸 **Confiance des consommateurs (US)** – indicateur clé du moral des ménages "
            "et de la dynamique de la demande."
        )

        # 🔹 Mercredi
        st.markdown("### 📌 Mercredi 26 Novembre")
        st.write("- 🇦🇺 **CPI Australie** – inflation importante pour la RBA.")
        st.write("- 🇳🇿 **Décision de taux RBNZ**.")
        st.write("- 🇺🇸 **PIB US (2e estimation)**.")
        st.write("- 🇺🇸 **PCE core & headline** – inflation préférée de la Fed.")

        # 🔹 Jeudi
        st.markdown("### 📌 Jeudi 27 Novembre")
        st.write("- 🇺🇸 **Thanksgiving (US)** – marchés américains quasi fermés.")
        st.write("- 🇯🇵 **Inflation Tokyo** – indicateur avancé.")

        # 🔹 Vendredi
        st.markdown("### 📌 Vendredi 28 Novembre")
        st.write("- 🇩🇪 **Ventes au détail Allemagne**.")
        st.write("- 🇨🇭 **PIB Suisse**.")
        st.write("- 🇩🇪 **Inflation préliminaire Allemagne**.")
        st.write("- 🇨🇦 **PIB Canada**.")


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
