# Vous avez les fonctions ici : 
# ratings_utils.py
import os
import glob
from typing import Optional, List, Dict

import pandas as pd
import streamlit as st

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
    # S&P / Fitch style
    if r.upper() in RATING_TO_SCORE:
        return RATING_TO_SCORE[r.upper()]
    # Moody's → mapping vers S&P
    if r in MOODYS_TO_SP:
        sp_equiv = MOODYS_TO_SP[r]
        return RATING_TO_SCORE.get(sp_equiv)
    return None


# --------------------------------------------------------------------
# 📊 Chargement des ratings agences
# --------------------------------------------------------------------

@st.cache_data
def load_ratings_2024(path: str = "rating2.xlsx"):
    """
    Charge le fichier rating2.xlsx, filtre 2024 et renvoie :
      - un pivot (index = Code/Country, colonnes = Agency, valeurs = Rating)
      - le nom de la colonne pays utilisée (Code ou Country)
    """
    if not os.path.exists(path):
        st.error("❌ rating2.xlsx introuvable.")
        return None, None

    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    if "Year" not in df:
        st.error("rating2.xlsx doit contenir une colonne 'Year'.")
        return None, None

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df_2024 = df[df["Year"] == 2024]

    if "Code" in df_2024:
        country_col = "Code"
    elif "Country" in df_2024:
        country_col = "Country"
    else:
        st.error("Aucune colonne 'Code' ou 'Country' trouvée dans rating2.xlsx.")
        return None, None

    pivot = df_2024.pivot_table(
        index=country_col,
        columns="Agency",
        values="Rating",
        aggfunc="first"
    ).sort_index()

    return pivot, country_col


# --------------------------------------------------------------------
# ⭐ Chargement ratings internes du modèle
# --------------------------------------------------------------------

@st.cache_data
def load_internal_ratings(pattern: str = "internal_ratings_*.xlsx"):
    """
    Charge le dernier fichier Excel de ratings internes correspondant au pattern.
    On suppose qu'il contient au moins les colonnes :
      - 'Code' : code du pays
      - 'predicted_cat' : catégorie entière
      - 'expected_score' : score continu
    """
    files = glob.glob(pattern)
    if not files:
        return None

    files.sort()
    df = pd.read_excel(files[-1])
    df.columns = [c.strip() for c in df.columns]
    return df
