import requests
import pandas as pd

IMF_BASE_URL = "https://www.imf.org/external/datamapper/api/v1"

COUNTRIES = [
    "FRA",  # France
    "GRC",  # Greece
    "JPN",  # Japan
    "USA",  # United States
    "ECU",  # Ecuador
    "VNM",  # Vietnam
    "ZAF",  # South Africa
    "ARG",  # Argentina
    "EGY",  # Egypt
    "GBR",  # United Kingdom
]

YEARS = list(range(2005, 2025))  # 2005–2024


def find_interest_indicator_id() -> str:
    """
    Va chercher dans /indicators l'ID de l'indicateur correspondant
    aux paiements d'intérêts (% PIB).
    """
    url = f"{IMF_BASE_URL}/indicators"
    print(f"👉 Appel catalogue IMF : {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    indicators = data["indicators"]

    candidates = []
    for ind_id, meta in indicators.items():
        label = (meta.get("label") or "").lower()
        desc = (meta.get("description") or "").lower()
        text = label + " " + desc

        # On cherche "interest" + "payment" dans label/description
        if "interest" in text and "payment" in text:
            candidates.append((ind_id, meta.get("label", "")))

    print("🔎 Candidats pour 'interest payments':")
    for cid, lab in candidates:
        print(f"  - {cid}: {lab}")

    if not candidates:
        raise RuntimeError("Aucun indicateur 'interest payments' trouvé dans le catalogue IMF.")

    # Pour l’instant on prend le premier candidat trouvé
    chosen_id = candidates[0][0]
    print(f"✅ Indicateur choisi : {chosen_id}")
    return chosen_id


def fetch_imf_debt_service(
    indicator_id: str | None = None,
    countries=COUNTRIES,
    years=YEARS,
) -> pd.DataFrame:
    """
    Récupère la 'charge de la dette' proxifiée par les paiements d'intérêts
    (% du PIB) pour la liste de pays / années.
    """

    if indicator_id is None:
        indicator_id = find_interest_indicator_id()

    periods_param = ",".join(str(y) for y in years)
    countries_param = "/".join(countries)

    url = f"{IMF_BASE_URL}/{indicator_id}/{countries_param}?periods={periods_param}"
    print(f"👉 Appel série IMF : {url}")

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Sécurité / debug
    if "values" not in data:
        print("⚠️ Réponse IMF inattendue, clés disponibles :", data.keys())
        raise RuntimeError("La réponse IMF ne contient pas 'values' (vérifie l'URL / l'indicateur).")

    if indicator_id not in data["values"]:
        print("⚠️ Indicateur introuvable dans 'values'.")
        print("Clés disponibles dans values :", data["values"].keys())
        raise RuntimeError(f"Indicateur {indicator_id} non trouvé dans la réponse IMF.")

    values = data["values"][indicator_id]

    rows = []
    for country in countries:
        country_series = values.get(country, {})
        if country_series is None:
            country_series = {}
        for year in years:
            year_str = str(year)
            value = country_series.get(year_str, None)
            rows.append(
                {
                    "country_code": country,
                    "year": year,
                    "debt_service_interest_pct_gdp": value,
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values(["country_code", "year"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df_debt_service = fetch_imf_debt_service()
    print(df_debt_service.head(20))

    output_path = "imf_debt_service_interest_10pays_2005_2024.xlsx"
    df_debt_service.to_excel(output_path, index=False)
    print(f"✅ Fichier sauvegardé : {output_path}")
