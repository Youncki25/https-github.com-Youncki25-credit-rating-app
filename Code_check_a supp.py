import pandas as pd

# =========================
# 1) Charger et nettoyer
# =========================

df = pd.read_excel("Ratings.xlsx")

# Normaliser les noms de colonnes (au cas où il y a des espaces)
df.columns = [c.strip() for c in df.columns]

# On garde uniquement l'essentiel
cols = ["Year", "Code", "rating_mean_num"]
df_clean = df[cols].drop_duplicates().sort_values(["Code", "Year"])

print("Aperçu des données nettoyées :")
print(df_clean.head())

# Sauvegarde propre (comme tu faisais)
df_clean.to_excel("ratings_mean_clean.xlsx", index=False)

# =========================
# 2) Trouver les années manquantes par pays
# =========================

# Période théorique des ratings (à adapter si besoin)
YEAR_START = 2000
YEAR_END = 2024
expected_years = set(range(YEAR_START, YEAR_END + 1))

missing_rows = []

for code, sub in df_clean.groupby("Code"):
    years_present = set(sub["Year"].dropna().astype(int))
    missing_years = sorted(expected_years - years_present)

    if missing_years:
        print(f"{code} → années manquantes : {missing_years}")
        for y in missing_years:
            missing_rows.append({"Code": code, "Year_missing": y})

# DataFrame avec toutes les années manquantes
df_missing = pd.DataFrame(missing_rows)

if not df_missing.empty:
    print("\n=== Tableau des années manquantes par pays ===")
    print(df_missing)

    # Export dans un fichier Excel pour vérifier tranquillement
    df_missing.to_excel("ratings_missing_years.xlsx", index=False)
    print("\n✅ Fichier 'ratings_missing_years.xlsx' généré.")
else:
    print("\n🎉 Aucun trou dans les années de ratings sur la période définie.")


x=16/(20*10)
print(x)