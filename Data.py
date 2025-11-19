# NE PAS RUN EN CHANGEANT LES PAYS DANS COUNTRIES SANS ADAPTER LES FICHIERS
# Ce script :
#   1) Télécharge les séries WB pour tous les WB_INDICATORS
#   2) Télécharge la dette FMI (GGXWDG_NGDP) pour 2000–2024
#   3) Télécharge aussi :
#        - l'inflation CPI FMI (PCPIPCH)
#        - le déficit FMI (GGXCNL_NGDP)
#        - la charge de la dette FMI (GGXINT_NGDP)
#   4) Met à jour les fichiers {COUNTRY}_WB_timeseries.xlsx :
#        - "Debt (% of GDP)" : OVERRIDE avec FMI 2000–2024
#        - "Inflation, consumer prices (annual %)" : COMPLÉTÉ avec FMI si NA
#        - "Net lending/borrowing (% of GDP)" : COMPLÉTÉ avec FMI si NA
#        - "Interest payments (% of GDP)" : COMPLÉTÉ avec FMI si NA

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
YEARS = "2000:2024"

# Période FMI pour les séries WEO
IMF_START_YEAR = 2000
IMF_END_YEAR = 2024

IMF_BASE_URL = "https://www.imf.org/external/datamapper/api/v1"

# Indicateur FMI WEO : General government gross debt (% of GDP)
IMF_DEBT_SERIES = "GGXWDG_NGDP"

# Indicateur FMI WEO : Net lending (+)/borrowing (–), % PIB (déficit)
IMF_DEFICIT_SERIES = "GGXCNL_NGDP"

# Indicateur FMI WEO : Inflation rate, average consumer prices (annual %)
# -> proxie pour "Inflation, consumer prices (annual %)"
IMF_CPI_SERIES = "PCPIPCH"

# Indicateur FMI WEO : General government interest payments, % PIB
IMF_INTEREST_SERIES = "GGXINT_NGDP"


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

    "Debt (% of GDP)": "GC.DOD.TOTL.GD.ZS",  # prendre (mais override par FMI 2000–2024)
    "Interest payments (% of GDP)": "GC.XPN.INTP.ZS",  # prendre (complété par FMI)
    "Tax revenue (% of GDP)": "GC.TAX.TOTL.GD.ZS",  # prendre
    "Net lending/borrowing (% of GDP)": "GC.NLD.TOTL.GD.ZS",  # prendre (complété par FMI)
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
# OUTILS FMI GÉNÉRIQUES
# =========================

def fetch_imf_series_all_countries(series_code, value_label):
    """
    Télécharge une série FMI (DataMapper) pour TOUS les pays de COUNTRIES
    entre IMF_START_YEAR et IMF_END_YEAR.

    Retourne un DataFrame : [Code, Year, value_label]
    """
    periods = ",".join(str(y) for y in range(IMF_START_YEAR, IMF_END_YEAR + 1))
    countries_param = "/".join(COUNTRIES)
    url = f"{IMF_BASE_URL}/{series_code}/{countries_param}?periods={periods}"

    print(f"→ FMI {series_code} pour tous les pays")
    # Debug :
    # print("   URL :", url)

    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    if "values" not in data or series_code not in data["values"]:
        print("⚠️ Réponse FMI inattendue pour", series_code, "- clés :", data.keys())
        return pd.DataFrame(columns=["Code", "Year", value_label])

    series_all = data["values"][series_code]

    rows = []
    for country in COUNTRIES:
        country_dict = series_all.get(country, {}) or {}
        for year_str, raw_val in country_dict.items():
            try:
                year = int(year_str)
            except ValueError:
                continue
            if not (IMF_START_YEAR <= year <= IMF_END_YEAR):
                continue
            val = float(raw_val) if raw_val is not None else None
            rows.append(
                {
                    "Code": country,
                    "Year": year,
                    value_label: val,
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
        df["Code"] = df["Code"].str.upper()

    return df


# =========================
# MAIN
# =========================

def main():
    # 1) Télécharger les séries FMI (dette, CPI, déficit, intérêts)
    print("===== Téléchargement FMI (Debt, CPI, Déficit, Intérêts) =====")

    df_imf_debt = fetch_imf_series_all_countries(
        IMF_DEBT_SERIES,
        "Debt (% of GDP)"
    )
    df_imf_cpi = fetch_imf_series_all_countries(
        IMF_CPI_SERIES,
        "Inflation, consumer prices (annual %) [IMF]"
    )
    df_imf_deficit = fetch_imf_series_all_countries(
        IMF_DEFICIT_SERIES,
        "Net lending/borrowing (% of GDP) [IMF]"
    )
    df_imf_interest = fetch_imf_series_all_countries(
        IMF_INTEREST_SERIES,
        "Interest payments (% of GDP) [IMF]"
    )

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

        # =========================
        # 2.a) Injection de la dette FMI (OVERRIDE)
        # =========================
        print(f"→ Injection de la dette FMI dans Debt (% of GDP) pour {COUNTRY}")
        imf_debt_c = (
            df_imf_debt[df_imf_debt["Code"] == COUNTRY]
            .set_index("Year")["Debt (% of GDP)"]
        )

        if "Debt (% of GDP)" not in ts.columns:
            ts["Debt (% of GDP)"] = pd.NA

        for year, val in imf_debt_c.items():
            if (year in ts.index) and (val is not None):
                # OVERRIDE systématique 2000–2024
                ts.loc[year, "Debt (% of GDP)"] = val

        # =========================
        # 2.b) CPI FMI -> compléter si NA
        # =========================
        print(f"→ Complétion CPI avec FMI pour {COUNTRY}")
        imf_cpi_c = (
            df_imf_cpi[df_imf_cpi["Code"] == COUNTRY]
            .set_index("Year")["Inflation, consumer prices (annual %) [IMF]"]
        )

        if "Inflation, consumer prices (annual %)" not in ts.columns:
            ts["Inflation, consumer prices (annual %)"] = pd.NA

        for year, val in imf_cpi_c.items():
            if (year in ts.index) and (val is not None):
                current = ts.loc[year, "Inflation, consumer prices (annual %)"]
                if pd.isna(current):
                    ts.loc[year, "Inflation, consumer prices (annual %)"] = val

        # =========================
        # 2.c) Déficit FMI -> compléter si NA
        # =========================
        print(f"→ Complétion Déficit (Net lending/borrowing) avec FMI pour {COUNTRY}")
        imf_def_c = (
            df_imf_deficit[df_imf_deficit["Code"] == COUNTRY]
            .set_index("Year")["Net lending/borrowing (% of GDP) [IMF]"]
        )

        if "Net lending/borrowing (% of GDP)" not in ts.columns:
            ts["Net lending/borrowing (% of GDP)"] = pd.NA

        for year, val in imf_def_c.items():
            if (year in ts.index) and (val is not None):
                current = ts.loc[year, "Net lending/borrowing (% of GDP)"]
                if pd.isna(current):
                    ts.loc[year, "Net lending/borrowing (% of GDP)"] = val

        # =========================
        # 2.d) Charge de la dette FMI -> compléter si NA
        # =========================
        print(f"→ Complétion Interest payments (% of GDP) avec FMI pour {COUNTRY}")
        imf_int_c = (
            df_imf_interest[df_imf_interest["Code"] == COUNTRY]
            .set_index("Year")["Interest payments (% of GDP) [IMF]"]
        )

        if "Interest payments (% of GDP)" not in ts.columns:
            ts["Interest payments (% of GDP)"] = pd.NA

        for year, val in imf_int_c.items():
            if (year in ts.index) and (val is not None):
                current = ts.loc[year, "Interest payments (% of GDP)"]
                if pd.isna(current):
                    ts.loc[year, "Interest payments (% of GDP)"] = val

        # 3) Sauvegarde du fichier pays
        out_path = f"{COUNTRY}_WB_timeseries.xlsx"
        ts.to_excel(out_path)
        print(f"✅ Fichier écrit : {out_path}")

    print("\n✅ FIN : WB + FMI téléchargé et intégré pour tous les pays.")


if __name__ == "__main__":
    main()
