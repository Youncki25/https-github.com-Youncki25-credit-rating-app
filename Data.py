# -*- coding: utf-8 -*-
# Check si environement ok, sinon ça va pas run

import time
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

COUNTRIES = [
    # Europe
    #"FRA","DEU","ITA","ESP","PRT","NLD","BEL","LUX","AUT","FIN","IRL",
    #"GRC","CYP","MLT",
    #"SVN","SVK","EST","LVA","LTU","POL","CZE","HUN","ROU","BGR",
    #"GBR","ISL","NOR","SWE","DNK","CHE",
    #"UKR","MDA","BLR","RUS","ALB","MKD","SRB","BIH","MNE","HRV"

    # Americas
    #"USA","CAN","MEX","ARG","BRA","CHL","COL","PER","ECU","URY","PRY","BOL","VEN",
    #"GTM","SLV","HND","NIC","CRI","PAN","DOM",

    # Asia-Pacific
    "CHN","JPN","KOR","IND","PAK","BGD","LKA","NPL","MDV","BTN",
    "IDN","MYS","SGP","THA","PHL","VNM","KHM","LAO","MMR","TLS","BRN",
    "AUS","NZL","FJI","PNG","WSM","TON","VUT","SLB","KIR",
   

    # Middle East & North Africa
    "TUR","EGY",

    # Sub-Saharan Africa
    "ZAF","NGA","GHA","CIV","SEN","MLI","BFA","NER","TCD","CMR","GAB","COG","COD",
    "UGA","KEN","TZA","RWA","BDI","ETH","SOM","SSD","SDN","ERI","DJI",
    "ZMB","MWI","MOZ","AGO","NAM","BWA","LSO","SWZ","MDG","COM","SYC","MUS",

]
   # pays 
YEARS = "2000:2024"                      

# fiscal, dette, déficit, inflation, balance commercial ( à ajouter)
# MG 
# voir les données  (trouver des facteurs), récup des fichier sur la croissance, inflation, Fiscal balance (revenus -dépenses), mettre une indicatrice sur le défault précédent ( c'est une idée on verra), indicatrice si c'est un pays industriel ou en développement, Ratings
WB_INDICATORS = {
    # ———————————————
    # ECONOMIC STRENGTH
    # ———————————————
    "GDP growth (annual %)": "NY.GDP.MKTP.KD.ZG",
    "GDP per capita (current US$)": "NY.GDP.PCAP.CD",
    "GDP per capita (PPP, international $)": "NY.GDP.PCAP.PP.CD",
    "GDP per capita growth (annual %)": "NY.GDP.PCAP.KD.ZG",
    "Inflation, consumer prices (annual %)": "FP.CPI.TOTL.ZG",
    "Population, total": "SP.POP.TOTL",
    "Life expectancy at birth (years)": "SP.DYN.LE00.IN",
    "Exports of goods and services (% of GDP)": "NE.EXP.GNFS.ZS",
    "Imports of goods and services (% of GDP)": "NE.IMP.GNFS.ZS",
    "Trade openness (% of GDP)": "NE.TRD.GNFS.ZS",

    # ———————————————
    # LABOR / SOCIAL
    # ———————————————
    "Unemployment (% labor force)": "SL.UEM.TOTL.ZS",
    "Poverty headcount ratio ($2.15/day)": "SI.POV.DDAY",
    "Gini index": "SI.POV.GINI",
    "Urban population (% of total)": "SP.URB.TOTL.IN.ZS",

    # ———————————————
    # FISCAL STRENGTH
    # ———————————————
    "Debt (% of GDP)": "GC.DOD.TOTL.GD.ZS",
    "Interest payments (% of GDP)": "GC.XPN.INTP.ZS",
    "Tax revenue (% of GDP)": "GC.TAX.TOTL.GD.ZS",
    "Net lending/borrowing (% of GDP)": "GC.NLD.TOTL.GD.ZS",
    "Government revenue (% of GDP)": "GC.REV.XGRT.GD.ZS",
    "Government expenditure (% of GDP)": "GC.XPN.TOTL.GD.ZS",
    "Cash surplus/deficit (% of GDP)": "GC.BAL.CASH.GD.ZS",
    "Government consumption (% of GDP)": "NE.CON.GOVT.ZS",
    "Military expenditure (% of GDP)": "MS.MIL.XPND.GD.ZS",

    # ———————————————
    # EXTERNAL / LIQUIDITY
    # ———————————————
    "Current account balance (% of GDP)": "BN.CAB.XOKA.GD.ZS",
    "Total reserves (current US$)": "FI.RES.TOTL.CD",
    "Total reserves (months of imports)": "FI.RES.TOTL.MO",
    "External debt stocks (current US$)": "DT.DOD.DECT.CD",
    "External debt stocks (% of GNI)": "DT.DOD.DECT.GN.ZS",

    # ———————————————
    # FINANCIAL / BANKING SECTOR
    # ———————————————
    "Domestic credit to private sector (% of GDP)": "FS.AST.PRVT.GD.ZS",
    "Bank nonperforming loans (% of gross loans)": "FB.AST.NPER.ZS",
    "Bank capital to assets ratio (%)": "FB.BNK.CAPA.ZS",
    "Bank liquid reserves to bank assets (%)": "FD.RES.LIQU.AS.ZS",

    # ———————————————
    # INSTITUTIONS & GOVERNANCE (WGI)
    # ———————————————
    "Control of Corruption": "CC.EST",
    "Government Effectiveness": "GE.EST",
    "Rule of Law": "RL.EST",
    "Voice and Accountability": "VA.EST",
    "Regulatory Quality": "RQ.EST",
    "Political Stability and Absence of Violence": "PV.EST",
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
        r = session.get(url, timeout=30)
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
