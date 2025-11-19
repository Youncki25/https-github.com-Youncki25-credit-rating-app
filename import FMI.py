import requests
import pandas as pd

# Tes pays
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

INDICATOR = "GGXWDG_NGDP"  # Dette brute des APU (% PIB), code WEO
START_YEAR = 2000
END_YEAR = 2024

BASE_URL = "https://www.imf.org/external/datamapper/api/v1"


def fetch_imf_debt(country: str) -> pd.DataFrame:
    """
    Récupère la série de dette publique (% PIB, GGXWDG_NGDP)
    pour un pays entre START_YEAR et END_YEAR via l'API DataMapper du FMI.
    """
    periods = ",".join(str(y) for y in range(START_YEAR, END_YEAR + 1))
    url = f"{BASE_URL}/{INDICATOR}/{country}?periods={periods}"

    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    # Structure typique DataMapper:
    # data["values"][INDICATOR][country]["2000"] -> valeur
    try:
        series = data["values"][INDICATOR][country]
    except KeyError:
        # Rien pour ce pays / indicateur
        return pd.DataFrame(columns=["Code", "Year", "Debt (% of GDP)"])

    rows = []
    for year_str, value in series.items():
        year = int(year_str)
        if START_YEAR <= year <= END_YEAR:
            # value peut être None
            val = float(value) if value is not None else None
            rows.append({"Code": country, "Year": year, "Debt (% of GDP)": val})

    return pd.DataFrame(rows)


# Boucle sur tous les pays
dfs = []
for c in COUNTRIES:
    print(f"Téléchargement FMI pour {c}...")
    df_c = fetch_imf_debt(c)
    dfs.append(df_c)

df_debt = pd.concat(dfs, ignore_index=True).sort_values(["Code", "Year"])

df_debt.to_excel("IMF_debt_2000_2024.xlsx", index=False)
print(df_debt.head())
