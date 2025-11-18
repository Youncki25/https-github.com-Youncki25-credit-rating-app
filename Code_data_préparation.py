import pandas as pd
import numpy as np

file_path = "/Users/beldjenna/Desktop/Rating Algo/Ratings.xlsx"

# Charger le fichier d'origine
df_ratings = pd.read_excel(file_path)

sp_fitch_map = {
    "AAA": 21,
    "AA+": 20, "AA": 19, "AA-": 18,
    "A+": 17,  "A": 16,  "A-": 15,
    "BBB+": 14, "BBB": 13, "BBB-": 12,
    "BB+": 11,  "BB": 10,  "BB-": 9,
    "B+": 8,    "B": 7,    "B-": 6,
    "CCC+": 5,  "CCC": 4,  "CCC-": 3,
    "CC": 2,
    "C": 1,
    "D": 0
}

moodys_map = {
    "Aaa": 21,
    "Aa1": 20, "Aa2": 19, "Aa3": 18,
    "A1": 17,  "A2": 16,  "A3": 15,
    "Baa1": 14, "Baa2": 13, "Baa3": 12,
    "Ba1": 11,  "Ba2": 10,  "Ba3": 9,
    "B1": 8,    "B2": 7,    "B3": 6,
    "Caa1": 5,  "Caa2": 4,  "Caa3": 3,
    "Ca": 2,
    "C": 1     # 1 (0 étant défaut type D)
}

def rating_to_num(agency, rating):
    if pd.isna(rating):
        return np.nan
    if agency in ["S&P", "Fitch"]:
        return sp_fitch_map.get(rating, np.nan)
    elif agency == "Moody's":
        return moodys_map.get(rating, np.nan)
    else:
        return np.nan

# Conversion rating texte → rating numérique
df_ratings["rating_num"] = df_ratings.apply(
    lambda row: rating_to_num(row["Agency"], row["Rating"]),
    axis=1
)

# Pivot : une ligne par (Country, Code, Year) avec une colonne par agence
df_pivot = df_ratings.pivot_table(
    index=["Country", "Code", "Year"],
    columns="Agency",
    values="rating_num"
)

# Moyenne des 3 agences
df_pivot["rating_mean_num"] = df_pivot[["S&P", "Fitch", "Moody's"]].mean(axis=1, skipna=True)

# On remet l’index à plat
df_mean = df_pivot.reset_index()

# Dictionnaire inverse pour reconstruire un rating texte "moyen"
inv_sp_fitch_map = {v: k for k, v in sp_fitch_map.items()}
df_mean["rating_mean_txt"] = df_mean["rating_mean_num"].round().map(inv_sp_fitch_map)

# ---- MERGE AVEC LE FICHIER D’ORIGINE ----
# On ne garde que les colonnes utiles pour ajouter au fichier initial
cols_to_add = ["Country", "Code", "Year", "rating_mean_num", "rating_mean_txt"]
df_export = df_ratings.merge(
    df_mean[cols_to_add],
    on=["Country", "Code", "Year"],
    how="left"
)

# Sauvegarde dans le MÊME fichier (même nom, mêmes données + colonnes ajoutées)
#df_export.to_excel(file_path, index=False)

# Optionnel : contrôler que ça marche
print(df_export.head())
print(df_export[df_export["Country"] == "France"].head())
