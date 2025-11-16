import glob, os
import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_GLOB = os.path.join(BASE_DIR, "*_WB_timeseries.xlsx")

@st.cache_data(show_spinner=False)
def _load_country_timeseries(file_list: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    out = {}
    for fp in file_list:
        iso = os.path.basename(fp).split("_")[0]

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

        # forcer toutes les colonnes en numérique
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

    # --------- Sidebar : choix du pays d'abord ----------
    with st.sidebar:
        st.markdown("####  Options des graphiques : ")
        sel_country = st.selectbox("Pays", countries, index=0)

    df = db[sel_country].copy()

    if df.empty:
        st.info(f"Pas de données pour {sel_country}.")
        return

    # s'assurer qu'on a bien un DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        st.error(f"Index de dates invalide pour {sel_country}.")
        return

    df = df.sort_index()

    # --- années disponibles ---
    years = df.index.year
    years = years[~pd.isna(years)]

    if years.empty:
        st.info(f"Aucune année valide pour {sel_country}.")
        return

    y_min = int(years.min())
    y_max = int(years.max())

    # --------- Slider sur les ANNÉES (ints) ----------
    with st.sidebar:
        if y_min == y_max:
            st.caption(f"Période disponible : {y_min} uniquement.")
            start_year = end_year = y_min
        else:
            start_year, end_year = st.slider(
                "Période (année)",
                min_value=y_min,
                max_value=y_max,
                value=(y_min, y_max),
                step=1,
            )

        rolling = st.number_input("Moyenne mobile (années)", 1, 10, 1, 1)
        normalize = st.checkbox("Indexer à 100 au début de la période", value=False)
        show_table = st.checkbox("Afficher le tableau sous les graphes", value=False)

    # --------- Filtrage & transformations ----------
    mask = (df.index.year >= start_year) & (df.index.year <= end_year)
    df = df.loc[mask]

    if rolling and rolling > 1:
        df = df.sort_index().rolling(rolling).mean()

    if normalize:
        first = df.dropna().iloc[0]
        df = (df / first) * 100

    st.markdown(f"#### {sel_country} — indicateurs")
    if df.empty or not len(df.columns):
        st.info("Pas de données sur cette période.")
        return

    for col in df.columns:
        st.markdown(f"**{col}**")
        st.line_chart(df[[col]].rename(columns={col: sel_country}), height=300)

        if show_table:
            st.dataframe(df[[col]].rename(columns={col: sel_country}).round(3))
