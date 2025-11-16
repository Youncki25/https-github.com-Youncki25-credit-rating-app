import glob, os
import numpy as np
import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_GLOB = os.path.join(BASE_DIR, "*_WB_timeseries.xlsx")

@st.cache_data(show_spinner=False)
def _load_country_timeseries(file_list: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    out = {}
    for fp in file_list:
        iso = os.path.basename(fp).split("_")[0]

        # lecture Excel
        try:
            df = pd.read_excel(fp)
        except Exception:
            df = pd.read_excel(fp, index_col=0)

        # --- colonne Date ---
        if "date" in df.columns:
            df = df.rename(columns={"date": "Date"})
        elif "Date" not in df.columns:
            df = df.rename(columns={df.columns[0]: "Date"})

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date").set_index("Date")

        # --- forcer toutes les colonnes en numérique ---
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        out[iso] = df[num_cols]

    return out


def render_macro_page():
    st.markdown("### Macroéconomie")

    file_list = tuple(sorted(glob.glob(DATA_GLOB)))
    db = _load_country_timeseries(file_list)

    if not db:
        st.error("Aucun fichier `*_WB_timeseries.xlsx` trouvé.")
        return

    countries = sorted(db.keys())
    st.caption(f"{len(countries)} pays chargés : {', '.join(countries)}")  # debug utile

    # --------- Sidebar contrôles ----------
    with st.sidebar:
        st.markdown("####  Options des graphiques : ")
        sel_country = st.selectbox("Pays", countries, index=0)
        df = db[sel_country].copy()

        min_d, max_d = df.index.min(), df.index.max()
        start, end = st.slider(
            "Période",
            min_value=min_d.to_pydatetime(),
            max_value=max_d.to_pydatetime(),
            value=(min_d.to_pydatetime(), max_d.to_pydatetime()),
            format="%Y",
        )
        rolling = st.number_input("Moyenne mobile (années)", 1, 10, 1, 1)
        normalize = st.checkbox("Indexer à 100 au début de la période", value=False)
        show_table = st.checkbox("Afficher le tableau sous les graphes", value=False)

    # --------- Filtrage & transformations ----------
    df = df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]

    if rolling and rolling > 1:
        df = df.sort_index().rolling(rolling).mean()

    if normalize:
        first = df.dropna().iloc[0]
        df = (df / first) * 100

    st.markdown(f"#### {sel_country} — indicateurs ({len(df.columns)} variables)")
    if df.empty or not len(df.columns):
        st.info("Pas de données sur cette période.")
        return

    for col in df.columns:
        st.markdown(f"**{col}**")
        st.line_chart(df[[col]].rename(columns={col: sel_country}), height=300)

        if show_table:
            st.dataframe(df[[col]].rename(columns={col: sel_country}).round(3))
