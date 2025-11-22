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
# Matthew dans page === Présentation

# ==============================
#  FONCTION : chargement rating2
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
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    # Vérif colonne Year
    if "Year" not in df.columns:
        st.error("La colonne 'Year' est manquante dans rating2.xlsx")
        return None, None

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df_2024 = df[df["Year"] == 2024].copy()

    # Détection de la colonne pays
    if "Code" in df_2024.columns:
        country_col = "Code"
    elif "Country" in df_2024.columns:
        country_col = "Country"
    else:
        st.error("Aucune colonne 'Code' ou 'Country' trouvée dans rating2.xlsx")
        return None, None

    # Vérif colonnes agence / rating
    needed = {"Agency", "Rating"}
    if not needed.issubset(df_2024.columns):
        st.error("rating2.xlsx doit contenir les colonnes 'Agency' et 'Rating'")
        return None, None

    # Pivot : un pays = une ligne, chaque agence = une colonne
    ratings_pivot = df_2024.pivot_table(
        index=country_col,
        columns="Agency",
        values="Rating",
        aggfunc="first"
    ).sort_index()

    return ratings_pivot, country_col


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

        # --- chargement des ratings 2024 ---
        ratings_2024, country_col = load_ratings_2024()

        st.markdown('<div class="card">', unsafe_allow_html=True)
        issuer = st.text_input("Nom de l'émetteur (affichage uniquement)")

        methodology = st.selectbox(
            "Méthodologie",
            ["Échelle S&P (AAA–D)", "Échelle Moody's (Aaa–C)", "Échelle Fitch (AAA–D)", "Échelle interne"],
        )

        # Si le fichier rating2 a bien été chargé
        if ratings_2024 is not None:
            # Choix du pays sur base du fichier Excel
            pays = st.selectbox(
                "Pays (code ISO / nom dans rating2)",
                options=ratings_2024.index.tolist()
            )

            # Mapping nom de méthodo -> colonne d'agence dans rating2
            methodology_to_agency = {
                "Échelle S&P (AAA–D)": "S&P",       # adapter au nom exact dans rating2.xlsx
                "Échelle Moody's (Aaa–C)": "Moody's",
                "Échelle Fitch (AAA–D)": "Fitch",
                "Échelle interne": None,
            }

            agence = methodology_to_agency[methodology]

            if agence is not None:
                if agence in ratings_2024.columns:
                    note_2024 = ratings_2024.loc[pays, agence]
                    st.markdown(
                        f"💡 **Note {agence} 2024 pour {pays} :** "
                        f"<span style='font-size:22px; font-weight:bold;'>{note_2024}</span>",
                        unsafe_allow_html=True
                    )
                else:
                    st.warning(
                        f"La colonne agence '{agence}' n'existe pas dans rating2.xlsx. "
                        "Vérifie le nom exact de la colonne (S&P, SP, etc.)."
                    )
            else:
                st.info("Aucune note d’agence associée pour l’échelle interne pour le moment.")

        st.markdown("</div>", unsafe_allow_html=True)

    elif page == "Macroéconomie":
        # Ta fonction existante
        render_macro_page()

    elif page == "Contact":
        st.markdown("### Contact")
        st.write("Ajoute ici des liens, emails ou formulaires de contact (Streamlit forms).")


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
