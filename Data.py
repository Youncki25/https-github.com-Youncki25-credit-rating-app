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
    "GDP growth (annual %)": "NY.GDP.MKTP.KD.ZG",
    "GDP per capita (current US$)": "NY.GDP.PCAP.CD",
    "Inflation, consumer prices (annual %)": "FP.CPI.TOTL.ZG",
    "Exports of goods and services (% of GDP)": "NE.EXP.GNFS.ZS",
    "Imports of goods and services (% of GDP)": "NE.IMP.GNFS.ZS",
    "Trade openness (% of GDP)": "NE.TRD.GNFS.ZS",


    "Unemployment (% labor force)": "SL.UEM.TOTL.ZS",
    "Gini index": "SI.POV.GINI",


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


    "Current account balance (% of GDP)": "BN.CAB.XOKA.GD.ZS",
    "Total reserves (current US$)": "FI.RES.TOTL.CD",
    "Total reserves (months of imports)": "FI.RES.TOTL.MO",
    "External debt stocks (current US$)": "DT.DOD.DECT.CD",
    "External debt stocks (% of GNI)": "DT.DOD.DECT.GN.ZS",
    "Foreign direct investment, net inflows (BoP, current US$)": "BX.KLT.DINV.CD.WD",
    "Foreign direct investment, net outflows (BoP, current US$)": "BM.KLT.DINV.CD.WD",

    # ———————————————
    # INSTITUTIONS & GOVERNANCE (WGI)
    # ———————————————
    "Control of Corruption": "CC.EST",
    "Political Stability and Absence of Violence": "PV.EST",
}
def make_session():
    s = requests.Session()
    r