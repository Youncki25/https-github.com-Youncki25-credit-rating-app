# NE PAS RUN  - SANS CHANGER LES PAYS SINON CA VA KRASH
import time
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

   # pays 
YEARS = "1990:2024"                      

# fiscal, dette, déficit, inflation, balance commercial ( à ajouter)
# MG 
# voir les données  (trouver des facteurs), récup des fichier sur la croissance, inflation, Fiscal balance (revenus -dépenses), mettre une indicatrice sur le défault précédent ( c'est une idée on verra), indicatrice si c'est un pays industriel ou en développement, Ratings
WB_INDICATORS = {
    # ———————————————
    # ECONOMIC STRENGTH
    # ———————————————

    # GDP niveau (courant)
    "GDP (current US$)": "NY.GDP.MKTP.CD", #Prendre

    # GDP croissance réelle
    "GDP growth (annual %)": "NY.GDP.MKTP.KD.ZG",

    # GDP per capita
    "GDP per capita (current US$)": "NY.GDP.PCAP.CD", #prendre

    # Inflation
    "Inflation, consumer prices (annual %)": "FP.CPI.TOTL.ZG", #prendre

    # Exportations / Importations
    "Exports of goods and services (% of GDP)": "NE.EXP.GNFS.ZS", #Prendre
    "Imports of goods and services (% of GDP)": "NE.IMP.GNFS.ZS", #prendre

    # Trade openness
    "Trade openness (% of GDP)": "NE.TRD.GNFS.ZS",  

    # Trade Balance = Exports – Imports (à calculer dans le code)
    # NOTE : pas de code direct → construit via les deux variables ci-dessus
    # Je l’inclus ici comme référence :
    "Trade Balance (% of GDP) [constructed]": None, # prendre

    # Unemployment
    "Unemployment (% labor force)": "SL.UEM.TOTL.ZS", #prendre

    # Gini
    "Gini index": "SI.POV.GINI", # prendre

    # ———————————————
    # FISCAL STRENGTH
    # ———————————————

    # Dette publique
    "Debt (% of GDP)": "GC.DOD.TOTL.GD.ZS", #prendre

    # Paiements d’intérêts
    "Interest payments (% of GDP)": "GC.XPN.INTP.ZS", # prendre

    # Recettes fiscales
    "Tax revenue (% of GDP)": "GC.TAX.TOTL.GD.ZS", # prendre

    # Net lending/borrowing (fiscal balance)
    "Net lending/borrowing (% of GDP)": "GC.NLD.TOTL.GD.ZS",

    # Government revenue
    "Government revenue (% of GDP)": "GC.REV.XGRT.GD.ZS",

    # Government spending
    "Government expenditure (% of GDP)": "GC.XPN.TOTL.GD.ZS",

    # Cash surplus/deficit
    "Cash surplus/deficit (% of GDP)": "GC.BAL.CASH.GD.ZS",

    # Government consumption
    "Government consumption (% of GDP)": "NE.CON.GOVT.ZS",

    # ———————————————
    # EXTERNAL SECTOR
    # ———————————————

    "Current account balance (% of GDP)": "BN.CAB.XOKA.GD.ZS", # prendre 
    "Total reserves (current US$)": "FI.RES.TOTL.CD", # prendre
    "Total reserves (months of imports)": "FI.RES.TOTL.MO",
    "External debt stocks (current US$)": "DT.DOD.DECT.CD", # prendre
    "External debt stocks (% of GNI)": "DT.DOD.DECT.GN.ZS", 
    "Foreign direct investment, net inflows (BoP, current US$)": "BX.KLT.DINV.CD.WD",
    "Foreign direct investment, net outflows (BoP, current US$)": "BM.KLT.DINV.CD.WD",

    # ———————————————
    # INSTITUTIONS & GOVERNANCE (WGI)
    # ———————————————
    "Control of Corruption": "CC.EST", # prendre
    "Political Stability and Absence of Violence": "PV.EST"
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
        r = session.get(url, timeout=20)
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
