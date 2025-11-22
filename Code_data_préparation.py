import pandas as pd
import numpy as np

# à chaque fois modifier le chemin ici : 
file_path =r"C:\Users\youne\https-github.com-Youncki25-credit-rating-app\Rating_API.xlsx"

# Lire l'Excel
df = pd.read_excel(file_path)

# ===== 2) Tables de conversion =====
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
    "C": 1
}

def rating_to_num(agency, rating):
    """Convertit un rating texte en score numérique selon l’agence."""
    if pd.isna(rating):
        return np.nan
    rating = str(rating).strip()
    if agency in ["S&P", "Fitch"]:
        return sp_fitch_map.get(rating, np.nan)
    elif agency == "Moody's":
        return moodys_map.get(rating, np.nan)
    return np.nan

# ===== 3) rating_numeric (ligne par ligne) =====
df["rating_numeric"] = df.apply(
    lambda row: rating_to_num(row["Agency"], row["Rating"]),
    axis=1
)

# ===== 4) rating_mean_num & rating_mean_ordinal =====
# On groupe par les colonnes d’identification disponibles
group_cols = [col for col in ["Country", "Code", "Year"] if col in df.columns]

df["rating_mean_num"] = df.groupby(group_cols)["rating_numeric"].transform("mean")

# Ordinal = arrondi au plus proche entier (avec gestion des NaN)
df["rating_mean_ordinal"] = df["rating_mean_num"].round().astype("Int64")

# ===== 5) Sauvegarde dans le même fichier =====
df.to_excel(file_path, index=False)

print("Colonnes ajoutées : rating_numeric, rating_mean_num, rating_mean_ordinal")
