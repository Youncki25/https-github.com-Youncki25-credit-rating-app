
# NE PAS RUN EN CHANGEANT LES PAYS DANS COUNTRIES SANS ADAPTER LES FICHIERS
# Ce script :
#   1) Télécharge les séries WB pour tous les WB_INDICATORS
#   2) Télécharge la dette FMI (GGXWDG_NGDP) pour 2000–2024
#   3) Remplit / remplace la colonne "Debt (% of GDP)" dans chaque
#      fichier {COUNTRY}_WB_timeseries.xlsx avec la dette FMI pour 2000–2024

import time
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =========================
# CONFIG
# =========================

COUNTRIES = [
    "FRA",  # France
    "GRC",  # Grèce
    "JPN",  # Japon
    "USA",  # États-Unis
    "ECU",  # Équateur
    "VNM",  # Vietnam
    "ZAF",  # Afrique du Sud
    "ARG",  # Argentine
    "EGY",  # Égypte
    "GBR",  # Royaume-Uni
]

# Période World Bank (toutes les variables)
YEARS = "1990:2024"

# Période FMI pour la dette
IMF_START_YEAR = 2000
IMF_END_YEAR = 2024

# Indicateur FMI WEO : General government gross debt (% of GDP)
IMF_DEBT_SERIES = "GGXWDG_NGDP"
IMF_BASE_URL = "https://www.imf.org/external/datamapper/api/v1"


# Variables WB (comme tu les avais)
WB_INDICATORS = {

    "GDP growth (annual %)": "NY.GDP.MKTP.KD.ZG",
    "GDP per capita (current US$)": "NY.GDP.PCAP.CD",  # prendre

    # Inflation
    "Inflation, consumer prices (annual %)": "FP.CPI.TOTL.ZG",  # prendre

    # Exportations / Importations
    "Exports of goods and services (% of GDP)": "NE.EXP.GNFS.ZS",  # Prendre
    "Imports of goods and services (% of GDP)": "NE.IMP.GNFS.ZS",  # prendre

    # Trade openness
    "Trade openness (% of GDP)": "NE.TRD.GNFS.ZS",

    # Trade Balance = Exports – Imports (construite dans le modèle si besoin)
    "Trade Balance (% of GDP) [constructed]": None,


    "Debt (% of GDP)": "GC.DOD.TOTL.GD.ZS",  # prendre (mais sera override par FMI 2000–2024)
    "Interest payments (% of GDP)": "GC.XPN.INTP.ZS",  # prendre
    "Tax revenue (% of GDP)": "GC.TAX.TOTL.GD.ZS",  # prendre
    "Net lending/borrowing (% of GDP)": "GC.NLD.TOTL.GD.ZS",
    "Government revenue (% of GDP)": "GC.REV.XGRT.GD.ZS",
    "Government expenditure (% of GDP)": "GC.XPN.TOTL.GD.ZS",

    "Current account balance (% of GDP)": "BN.CAB.XOKA.GD.ZS",  # prendre


    "Control of Corruption": "CC.EST",  # prendre
    "Political Stability and Absence of Violence": "PV.EST",
}

# Liste canonique utilisée dans le modèle économétrique
WB_INDICATORS_CANON = [
    "GDP growth (annual %)",
    "GDP per capita (current US$)",
    "Inflation, consumer prices (annual %)",
    "Trade openness (% of GDP)",
    "Debt (% of GDP)",
    "Net lending/borrowing (% of GDP)",
    "Current account balance (% of GDP)",
    "Control of Corruption",
    "Political Stability and Absence of Violence",
]


# =========================
# OUTIL WB
# =========================

def make_session():
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "wb-client/1.0"})
    return s


def wb_fetch_paginated(ind_code, country, years, per_page=1000):
    """Télécharge une série WB paginée pour un pays."""
    if ind_code is None:
        # Pour la série "Trade Balance [constructed]" par ex.
        return pd.DataFrame(columns=["date", "value"])

    session = make_session()
    base = (
        "https://api.worldbank.org/v2/country/{}/indicator/{}"
        "?format=json&date={}&per_page={}&page={}"
    )

    rows, page, total_pages = [], 1, None

    while True:
        url = base.format(country, ind_code, years, per_page, page)
        r = session.get(url, timeout=25)
        try:
            r.raise_for_status()
            data = r.json()
        except Exception:
            break

        if not isinstance(data, list) or len(data) < 2 or data[1] is None:
            break

        if total_pages is None:
            total_pages = int(data[0].get("pages", 1))

        for row in data[1]:
            rows.append({"date": int(row["date"]), "value": row["value"]})

        if page >= total_pages:
            break

        page += 1
        time.sleep(0.1)

    return pd.DataFrame(rows)


# =========================
# OUTIL FMI
# =========================

def fetch_imf_debt(country):
    """
    Télécharge la dette FMI (GGXWDG_NGDP) pour un pays
    entre IMF_START_YEAR et IMF_END_YEAR.
    """
    periods = ",".join(str(y) for y in range(IMF_START_YEAR, IMF_END_YEAR + 1))
    url = f"{IMF_BASE_URL}/{IMF_DEBT_SERIES}/{country}?periods={periods}"

    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    try:
        series = data["values"][IMF_DEBT_SERIES][country]
    except KeyError:
        return pd.DataFrame(columns=["Code", "Year", "Debt (% of GDP)"])

    rows = []
    for year_str, value in series.items():
        year = int(year_str)
        if IMF_START_YEAR <= year <= IMF_END_YEAR:
            val = float(value) if value is not None else None
            rows.append(
                {"Code": country, "Year": year, "Debt (% of GDP)": val}
            )

    return pd.DataFrame(rows)


# =========================
# MAIN
# =========================

def main():
    # 1) Télécharger la dette FMI pour tous les pays une fois
    print("===== Téléchargement dette FMI (GGXWDG_NGDP) =====")
    imf_frames = []
    for c in COUNTRIES:
        print(f"→ FMI pour {c} ...")
        df_c = fetch_imf_debt(c)
        imf_frames.append(df_c)
    df_imf = pd.concat(imf_frames, ignore_index=True)
    df_imf["Year"] = pd.to_numeric(df_imf["Year"], errors="coerce").astype("Int64")
    df_imf["Code"] = df_imf["Code"].str.upper()

    # 2) Boucle WB + fusion FMI par pays
    for COUNTRY in COUNTRIES:
        print(f"\n===== Téléchargement WB pour {COUNTRY} ({YEARS}) =====")

        frames = []
        for label, code in WB_INDICATORS.items():
            print(f"→ {label} [{code}] ...")
            df = wb_fetch_paginated(code, COUNTRY, YEARS)
            if df.empty:
                continue
            df["Series Name"] = label
            frames.append(df)

        if not frames:
            print(f"Aucune donnée WB pour {COUNTRY}, on passe.")
            continue

        dataset = pd.concat(frames, ignore_index=True)

        # Pivot en time-series
        ts = dataset.pivot_table(
            index="date",
            columns="Series Name",
            values="value",
            aggfunc="first",
        )
        ts = ts.sort_index()

        # 2.b) Remplacer / compléter la dette WB par la dette FMI 2000–2024
        print(f"→ Injection de la dette FMI dans Debt (% of GDP) pour {COUNTRY}")
        imf_c = df_imf[df_imf["Code"] == COUNTRY].set_index("Year")["Debt (% of GDP)"]

        # s'assurer que la colonne existe
        if "Debt (% of GDP)" not in ts.columns:
            ts["Debt (% of GDP)"] = pd.NA

        # override sur les années où FMI a une valeur
        for year, val in imf_c.items():
            if (year in ts.index) and (val is not None):
                ts.loc[year, "Debt (% of GDP)"] = val

        # 3) Sauvegarde du fichier pays
        out_path = f"{COUNTRY}_WB_timeseries.xlsx"
        ts.to_excel(out_path)
        print(f"✅ Fichier écrit : {out_path}")

    print("\n✅ FIN : WB + FMI téléchargé et intégré pour tous les pays.")


if __name__ == "__main__":
    main()
