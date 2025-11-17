# NE PAS RUN  - SANS CHANGER LES PAYS SINON CA VA KRASH
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
    "Debt (% of GDP)": "GC.DO