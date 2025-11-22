# ui_streamlit.py
import streamlit as st
from dataclasses import dataclass
from typing import Optional, List, Dict
import base64, os, uuid, glob
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
# 📌 Mapping des notations vers score ordinal commun (1–22)
# --------------------------------------------------------------------

RATING_ORDER = [
    "AAA","AA+","AA","AA-","A+","A","A-",
    "BBB+","BBB","BBB-","BB+","BB","BB-",
    "B+","B","B-","CCC+","CCC","CCC-","CC","C","D"
]

RATING_TO_SCORE = {r: i + 1 for i, r in enumerate(RATING_ORDER)}

MOODYS_TO_SP = {
    "Aaa":"AAA","Aa1":"AA+","Aa2":"AA","Aa3":"AA-",
    "A1":"A+","A2":"A","A3":"A-",
    "Baa1":"BBB+","Baa2":"BBB","Baa3":"BBB-",
    "Ba1":"BB+","Ba2":"BB","Ba3":"BB-",
    "B1":"B+","B2":"B","B3":"B-",
    "Caa1":"CCC+","Caa2":"CCC","Caa3":"CCC-",
    "Ca":"CC","C":"C"
}

def score_to_rating(score: int) -> str:
    """Convertit un score ordinal (1–22) → notation AAA–D."""
    if score is None or pd.isna(score):
        return "N/A"
    score = int(score)
    if 1 <= score <= len(RATING_ORDER):
        return RATING_ORDER[score - 1]
    return "N/A"

def rating_to_ordinal(r: Optional[str]) -> Optional[int]:
    """Convertit notation S&P / Fitch / Moody’s → score ordinal."""
    if r is None or (isinstance(r, float) and pd.isna(r)):
        return None
    r = str(r).strip()
    if r.upper() in RATING_TO_SCORE:
        return RATING_TO_SCORE[r.upper()]
    if r in MOODYS_TO_SP:
        return RATING_TO_SCORE.get(MOODYS_TO_SP[r])
    return None


# --------------------------------------------------------------------
# 👥 Gestion des profils d'analystes
# --------------------------------------------------------------------

@dataclass
class Analyst:
    id: str
    name: str
    role: str
    b64: Optional[str] = None
    validated: bool = False


def _img_to_b64(path: str):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def _build_from_config(config: List[Dict]):
    out = []
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


def _render_sidebar():
    st.sidebar.markdown("### Menu")
    page = st.sidebar.radio(
        "Navigation",
        ["Présentation", "Simulation de la note", "Macroéconomie", "Contact"],
        index=0,
    )
    st.sidebar.markdown("---")
    return page


def _render_profiles_panel():
    st.markdown("### Profils")
    if not st.session_state.profiles:
        st.caption("Aucun profil. Cliquez sur Reset.")
    else:
        for prof in st.session_state.profiles:
            c1, c2, c3, c4 = st.columns([1,3,1,1])
            with c1:
                if prof.b64:
                    st.markdown(
                        f"<img class='face' src='data:image/png;base64,{prof.b64}'/>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("<div class='card small'>Image manquante</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{prof.name}**<br/>{prof.role}", unsafe_allow_html=True)
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


# --------------------------------------------------------------------
# 📊 Chargement des ratings agences
# --------------------------------------------------------------------

@st.cache_data
def load_ratings_2024(path="rating2.xlsx"):
    if not os.path.exists(path):
        st.error("❌ rating2.xlsx introuvable.")
        return None, None

    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    if "Year" not in df:
        st.error("rating2.xlsx doit contenir Year.")
        return None, None

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df_2024 = df[df["Year"] == 2024]

    if "Code" in df_2024: country_col="Code"
    elif "Country" in df_2024: country_col="Country"
    else:
        st.error("Aucune colonne Code / Country.")
        return None, None

    pivot = df_2024.pivot_table(
        index=country_col, columns="Agency", values="Rating", aggfunc="first"
    ).sort_index()

    return pivot, country_col


# --------------------------------------------------------------------
# ⭐ Chargement ratings internes du modèle
# --------------------------------------------------------------------

@st.cache_data
def load_internal_ratings(pattern="internal_ratings_*.xlsx"):
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort()
    df = pd.read_excel(files[-1])
    df.columns = [c.strip() for c in df.columns]
    return df


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
        st.write("Nous avons construit un modèle de notation souveraine basé sur des données API...")
        st.markdown("[Voir documentation du modèle](https://ton-lien-ici.com)")

    # ------------------------------------------------------
    # 📌 SIMULATION DE LA NOTE
    # ------------------------------------------------------
    elif page == "Simulation de la note":

        st.markdown("### Simulation de la note")
        st.write(
            "Vous trouverez ci-dessous les notations souveraines 2024 des trois principales agences "
            "ainsi que la note calculée par notre modèle interne."
        )

        ratings_2024, country_col = load_ratings_2024()
        internal_ratings = load_internal_ratings()

        if ratings_2024 is None:
            st.warning("Aucune notation agence disponible.")
            return

        st.markdown('<div class="card">', unsafe_allow_html=True)

        methodology = st.selectbox(
            "Méthodologie",
            ["Échelle S&P (AAA–D)", "Échelle Moody's (Aaa–C)", "Échelle Fitch (AAA–D)", "Échelle interne"]
        )

        pays = st.selectbox("Pays", ratings_2024.index.tolist())

        methodology_to_agency = {
            "Échelle S&P (AAA–D)": "S&P",
            "Échelle Moody's (Aaa–C)": "Moody's",
            "Échelle Fitch (AAA–D)": "Fitch",
            "Échelle interne": None
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
                    unsafe_allow_html=True
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
                        unsafe_allow_html=True
                    )

                    st.caption(
                        f"Score continu estimé : {expected:.2f} • Catégorie : {cat} • Équivalent lettre : {letter}"
                    )

        # ---- Tableau récap ----
        st.markdown("---")
        st.markdown(f"**Résumé des notations 2024 pour {pays}**")

        row_letters = ratings_2024.loc[pays]
        df_rec = pd.DataFrame({
            "Agence": row_letters.index,
            "Notation": row_letters.values
        })
        df_rec["Score ordinal"] = df_rec["Notation"].apply(rating_to_ordinal)

        st.dataframe(df_rec.set_index("Agence"))

        st.markdown("</div>", unsafe_allow_html=True)


    # ------------------------------------------------------
    # MACRO
    # ------------------------------------------------------
    elif page == "Macroéconomie":
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
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    page = _render_sidebar()

    if "profiles" not in st.session_state:
        st.session_state.profiles = _build_from_config(ANALYSTS_CONFIG)

    left, right = st.columns([5,2])
    with left:
        _render_page_content(page)
    with right:
        _render_profiles_panel()
