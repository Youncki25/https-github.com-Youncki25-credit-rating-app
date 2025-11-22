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

# ========= MAPPING DES NOTES → SCORE ORDINAL COMMUN =========

# Échelle S&P / Fitch standard (22 crans)
RATING_ORDER = [
    "AAA",
    "AA+",
    "AA",
    "AA-",
    "A+",
    "A",
    "A-",
    "BBB+",
    "BBB",
    "BBB-",
    "BB+",
    "BB",
    "BB-",
    "B+",
    "B",
    "B-",
    "CCC+",
    "CCC",
    "CCC-",
    "CC",
    "C",
    "D",
]

RATING_TO_SCORE = {rat: i + 1 for i, rat in enumerate(RATING_ORDER)}

# Correspondance Moody's → notation S&P/Fitch
MOODYS_TO_SP = {
    "Aaa": "AAA",
    "Aa1": "AA+",
    "Aa2": "AA",
    "Aa3": "AA-",
    "A1": "A+",
    "A2": "A",
    "A3": "A-",
    "Baa1": "BBB+",
    "Baa2": "BBB",
    "Baa3": "BBB-",
    "Ba1": "BB+",
    "Ba2": "BB",
    "Ba3": "BB-",
    "B1": "B+",
    "B2": "B",
    "B3": "B-",
    "Caa1": "CCC+",
    "Caa2": "CCC",
    "Caa3": "CCC-",
    "Ca": "CC",
    "C": "C",
}

def rating_to_ordinal(rating: Optional[str]) -> Optional[int]:
    """
    Convertit une notation en score ordinal (1 = AAA, ..., 22 = D)
    en harmonisant S&P / Fitch / Moody's.
    """
    if rating is None or (isinstance(rating, float) and pd.isna(rating)):
        return None

    r = str(rating).strip()

    # D'abord : on essaie direct sur la grille S&P/Fitch
    r_up = r.upper()
    if r_up in RATING_TO_SCORE:
        return RATING_TO_SCORE[r_up]

    # Moody's : on garde la casse (Aaa, Aa1, ...)
    if r in MOODYS_TO_SP:
        sp_equiv = MOODYS_TO_SP[r]
        return RATING_TO_SCORE.get(sp_equiv)

    # Cas type "NR", "N/A", etc. → None
    return None


# ========= DATACLASS ANALYSTE & UI PROFILS =========

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

# ==============================
#  FONCTION : chargement rating2 (agences)
# ==============================
@st.cache_data
def load_ratings_2024(path: str = "rating2.xlsx"):
    """
    Lit le fichier rating2.xlsx et renvoie :
    - un pivot (index = pays, colonnes = agences, valeurs = rating en 2024)
    - le nom de la colonne pays utilisée ("Code" ou "Country")
    ATTEND dans rating2.xlsx au moins les colonnes :
        Year, Agency, Rating, Code (ou Country)
    """
    if not os.path.exists(path):
        st.error(f"❌ Fichier '{path}' introuvable.")
        return None, None

    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    if "Year" not in df.columns:
        st.error("La colonne 'Year' est manquante dans rating2.xlsx")
        return None, None

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df_2024 = df[df["Year"] == 2024].copy()

    if df_2024.empty:
        st.warning("Aucune observation pour l'année 2024 dans rating2.xlsx.")
        return None, None

    if "Code" in df_2024.columns:
        country_col = "Code"
    elif "Country" in df_2024.columns:
        country_col = "Country"
    else:
        st.error("Aucune colonne 'Code' ou 'Country' trouvée dans rating2.xlsx")
        return None, None

    needed = {"Agency", "Rating"}
    if not needed.issubset(df_2024.columns):
        st.error("rating2.xlsx doit contenir les colonnes 'Agency' et 'Rating'")
        return None, None

    ratings_pivot = df_2024.pivot_table(
        index=country_col,
        columns="Agency",
        values="Rating",
        aggfunc="first"
    ).sort_index()

    return ratings_pivot, country_col

# ==============================
#  FONCTION : chargement notes internes (modèle)
# ==============================
@st.cache_data
def load_internal_ratings(pattern: str = "internal_ratings_*.xlsx"):
    """
    Charge le fichier des notes internes exporté par le modèle :
    colonnes attendues : Code, Year, expected_score, predicted_cat
    """
    files = glob.glob(pattern)
    if not files:
        return None

    files.sort()
    latest = files[-1]  # dernier fichier = dernière année estimée

    try:
        df = pd.read_excel(latest)
    except Exception as e:
        st.error(f"Erreur lors de la lecture des notes internes ({latest}) : {e}")
        return None

    df.columns = [c.strip() for c in df.columns]

    for col in ["Code", "Year", "expected_score"]:
        if col not in df.columns:
            st.error("Le fichier de notes internes doit contenir au minimum 'Code', 'Year' et 'expected_score'.")
            return None

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)

    return df

# ==============================
#  CONTENU DES PAGES
# ==============================
def _render_page_content(page: str):
    st.markdown("# 💹  Calculateur de Note")
    st.caption(
        "Vous pouvez déterminer la note de crédit d'un émetteur souverain en utilisant notre modèle de notation transparent."
        " Cette application vous permet d'explorer les données macroéconomiques des pays et d'avoir un point de vue des analystes."
    )
    st.markdown("---")

    if page == "Présentation":
        st.markdown("### Explication du projet et de l'outil mis à disposition :")
        st.write(
            "Bonjour, "
            "Nous sommes ravis de vous compter parmi nos destinataires. Nous sommes des étudiants et, dans le cadre d’un projet visant à élaborer un modèle de notation d’une entité souveraine, nous avons développé ce calculateur. Les données utilisées sont récupérées via des API : aucune donnée ne provient d’un fichier Excel téléchargé à une date précise. Cela a complexifié notre approche, mais rend l’outil plus régulièrement utilisable. "
            "Dans la section « Modèle », vous trouverez un document détaillant notre approche économétrique ainsi que les limites d’utilisation de notre outil de rating. Vous trouverez également nos coordonnées : nous sommes ouverts à tout retour ou commentaire."
        )
        st.write(
            "Nous avons poussé l’analyse un peu plus loin en développant un outil supplémentaire particulièrement intéressant : le calcul de lignes de risque (VaR pour des produits dérivés). Cet outil, couramment utilisé en salle de marché pour mesurer et suivre les expositions, nous a permis d’explorer plus en profondeur les méthodes de gestion du risque. Il était pour nous très instructif de plonger dans ce type d’approche et d’en proposer une mise en pratique concrète au sein de notre projet."
        )
        st.markdown("[📄 Voir le modèle de rating](https://ton-lien-ici.com)")

    elif page == "Simulation de la note":
        st.markdown("### Simulation de la note")
        st.write(
            "Vous trouverez ci-dessous les notations souveraines 2024 des trois principales agences, "
            "ainsi que la note estimée par notre modèle. Cela vous permet de comparer l’évaluation "
            "des agences avec notre approche économétrique interne, sur une échelle ordinale commune."
        )

        ratings_2024, country_col = load_ratings_2024()
        internal_ratings = load_internal_ratings()

        if ratings_2024 is None:
            st.info("Les notations des agences ne sont pas disponibles pour le moment.")
            return

        st.markdown('<div class="card">', unsafe_allow_html=True)

        methodology = st.selectbox(
            "Méthodologie",
            ["Échelle S&P (AAA–D)", "Échelle Moody's (Aaa–C)", "Échelle Fitch (AAA–D)", "Échelle interne"],
        )

        pays = st.selectbox(
            "Pays (code ISO / nom dans rating2)",
            options=ratings_2024.index.tolist()
        )

        methodology_to_agency = {
            "Échelle S&P (AAA–D)": "S&P",
            "Échelle Moody's (Aaa–C)": "Moody's",
            "Échelle Fitch (AAA–D)": "Fitch",
            "Échelle interne": None,
        }

        agence = methodology_to_agency[methodology]

        # ========= 1) Cas agences externes =========
        if agence is not None:
            if agence in ratings_2024.columns:
                note_2024 = ratings_2024.loc[pays, agence]
                score_ord = rating_to_ordinal(note_2024)

                st.markdown(
                    f"💡 **Note {agence} 2024 pour {pays} :** "
                    f"<span style='font-size:22px; font-weight:bold;'>{note_2024}</span>",
                    unsafe_allow_html=True
                )
                if score_ord is not None:
                    st.caption(f"Score ordinal associé : {score_ord} (1 = AAA, 22 = D)")
                else:
                    st.caption("Score ordinal non défini pour cette notation.")
            else:
                st.warning(
                    f"La colonne agence '{agence}' n'existe pas dans rating2.xlsx. "
                    "Vérifie le nom exact de la colonne (S&P, SP, etc.)."
                )

        # ========= 2) Cas échelle interne =========
        else:
            if internal_ratings is None:
                st.info("Les notes internes ne sont pas encore disponibles (fichier internal_ratings_*.xlsx manquant).")
            else:
                code = pays  # on suppose que l'index de ratings_2024 est le code pays

                years_avail = internal_ratings["Year"].unique()
                target_year = 2024 if 2024 in years_avail else int(internal_ratings["Year"].max())

                row = internal_ratings[
                    (internal_ratings["Code"] == code) &
                    (internal_ratings["Year"] == target_year)
                ]

                if row.empty:
                    st.warning(f"Aucune note interne disponible pour {code} en {target_year}.")
                else:
                    expected_score = row["expected_score"].iloc[0]
                    st.markdown(
                        f"💡 **Note interne (score attendu) {target_year} pour {code} :** "
                        f"<span style='font-size:22px; font-weight:bold;'>{expected_score:.2f}</span>",
                        unsafe_allow_html=True
                    )
                    if "predicted_cat" in row.columns:
                        cat = int(row["predicted_cat"].iloc[0])
                        st.caption(
                            f"Catégorie ordinale la plus probable (échelle interne) : {cat} "
                            "(1 = AAA, 22 = D, même grille que les agences)."
                        )

        # ========= 3) Tableau récap : lettres + scores pour TOUTES les agences =========
        st.markdown("---")
        st.markdown(f"**Résumé des notations 2024 pour {pays} (agences externes)**")

        row_letters = ratings_2024.loc[pays].copy()  # Series : index = agences, values = rating lettre
        df_rec = pd.DataFrame({
            "Agence": row_letters.index,
            "Notation": row_letters.values,
        })
        df_rec["Score ordinal"] = df_rec["Notation"].apply(rating_to_ordinal)

        st.dataframe(df_rec.set_index("Agence"))

        st.markdown("</div>", unsafe_allow_html=True)

    elif page == "Macroéconomie":
        render_macro_page()

    elif page == "Contact":
        st.markdown("### Contact")
        st.write("Ajoute ici des liens, emails ou formulaires de contact (Streamlit forms).")


def launch_dashboard():
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    page = _render_sidebar()

    if "profiles" not in st.session_state:
        st.session_state.profiles = _build_from_config(ANALYSTS_CONFIG)

    left, right = st.columns([5, 2])
    with left:
        _render_page_content(page)
    with right:
        _render_profiles_panel()
