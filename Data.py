# -*- coding: utf-8 -*-
# Check si environement ok, sinon ça va pas run

import time
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

COUNTRIES = ["FRA", "ARG","ZAF", "EGY", "VNM","MEX","IND","CAN","DEU","JPN"]    # pays 
YEARS = "2000:2024"                      


# voir les données  (trouver des facteurs), récup des fichier sur la croissance, inflation, Fiscal balance (revenus -dépenses), mettre une indicatrice sur le défault précédent ( c'est une idée on verra), indicatrice si c'est un pays industriel ou en développement, Ratings
WB_INDICATORS = {
    "GDP growth (annual %)": "NY.GDP.MKTP.KD.ZG",
    "Inflation, consumer prices (annual %)": "FP.CPI.TOTL.ZG",
    "Unemployment (% labor force)": "SL.UEM.TOTL.ZS",
    "Interest payments (% of GDP)": "GC.XPN.INTP.ZS",
    "Tax revenue (% of GDP)": "GC.TAX.TOTL.GD.ZS",
}

def make_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5,
                  status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "wb-client/1.0"})
    return s
# extraction 
def wb_fetch_paginated(ind_code, country, years, per_page=1000):
    session = make_session()
    base = ("https://api.worldbank.org/v2/country/{}/indicator/{}"
            "?format=json&date={}&per_page={}&page={}")
    rows, page, total_pages = [], 1, None

    while True:
        url = base.format(country, ind_code, years, per_page, page)
        r = session.get(url, timeout=10)
        try:
            r.raise_for_status()
            data = r.json()
        except:
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
# follow up du téléchargement
for COUNTRY in COUNTRIES:
    print(f"\n===== Téléchargement pour {COUNTRY} ({YEARS}) =====")

    frames = []
    for label, code in WB_INDICATORS.items():
        print(f"→ {label} [{code}] ...")
        df = wb_fetch_paginated(code, COUNTRY, YEARS)
        df["Series Name"] = label
        frames.append(df)

    dataset = pd.concat(frames, ignore_index=True)

    # Pivot en time-series
    ts = dataset.pivot_table(index="date", columns="Series Name", values="value", aggfunc="first")
    ts = ts.sort_index()

    out_path = f"{COUNTRY}_WB_timeseries.xlsx"
    ts.to_excel(out_path)
    print(f"✅ Fichier écrit : {out_path}")
