import os
import pandas as pd
import streamlit as st

from ratings_utils import load_internal_ratings

# =======================================================================================
#  🔥 1) CHARGE LE DATASET UTILISÉ PAR LE MODÈLE (déjà interpolé & propre)
# =======================================================================================

@st.cache_data(show_spinner=False)
def load_model_dataset(base_dir: str) -> pd.DataFrame:
    path = os.path.join(base_dir, "model_dataset.xlsx")
    if not os.path.exists(path):
        st.error(f"❌ Fichier introuvable : {path}. Lance ton script pour le générer.")
        return pd.DataFrame()

    df = pd.read_excel(path)
    df = df.sort_values(["Code", "Year"])
    return df


# =======================================================================================
#  🔥 2) RENDER MACRO PAGE — Basé 100% sur df_model (plus sur les fichiers WB bruts)
# =======================================================================================

def render_macro_page():

    st.markdown("### Données macroéconomiques")
    st.write("Visualisation des indicateurs macro utilisés dans notre modèle interne.")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    df = load_model_dataset(base_dir)

    if df.empty:
        return

    # Colonnes macro du modèle
    macro_cols = [
        "GDP growth (annual %)",
        "GDP per capita (current US$)",
        "Debt (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "Control of Corruption",
        "Interest payments (% of GDP)"
    ]

    # ===================================================================================
    # 1) Filtrer uniquement les pays présents dans les ratings internes
    # ===================================================================================
    internal_ratings = load_internal_ratings()
    if internal_ratings is None:
        st.error("❌ Aucun rating interne trouvé (internal_ratings_*.xlsx manquant).")
        return

    internal_codes = set(internal_ratings["Code"].unique())
    df = df[df["Code"].isin(internal_codes)]

    # ===================================================================================
    # 2) Filtrer uniquement les années 2000–2024
    # ===================================================================================
    df = df[(df["Year"] >= 2000) & (df["Year"] <= 2024)]

    codes = sorted(df["Code"].unique())

    # === Selecteur de pays ===
    with st.sidebar:
        st.markdown("#### Options des graphiques")
        sel_code = st.selectbox("Pays", codes)

        show_table = st.checkbox("Afficher le tableau sous les graphes", value=False)


    df_country = df[df["Code"] == sel_code].copy()
    df_country = df_country.set_index("Year")

    st.markdown(f"### {sel_code} — indicateurs macro (2000–2024)")

    # ===================================================================================
    # 3) Affichage des graphes pour chaque indicateur du modèle
    # ===================================================================================
    for col in macro_cols:

        if col not in df_country.columns:
            continue

        st.markdown(f"**{col}**")
        st.line_chart(
            df_country[[col]].rename(columns={col: sel_code}),
            height=300
        )

        if show_table:
            st.dataframe(df_country[[col]].round(3))
