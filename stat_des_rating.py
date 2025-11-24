import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ============================================================
# 0. Chemin Windows
# ============================================================
BASE_DIR = r"C:\Users\youne\https-github.com-Youncki25-credit-rating-app"
rating_file = os.path.join(BASE_DIR, "ratings_annual_per_agency_filled.xlsx")

# Chargement
df = pd.read_excel(rating_file)
df.columns = [c.strip() for c in df.columns]

# ============================================================
# 1. Liste S&P, conversion Moody's -> S&P
# ============================================================

rating_letter_to_num = {
    "AAA": 22, "AA+": 21, "AA": 20, "AA-": 19,
    "A+": 18,  "A": 17,   "A-": 16,
    "BBB+": 15, "BBB": 14, "BBB-": 13,
    "BB+": 12,  "BB": 11,  "BB-": 10,
    "B+": 9,    "B": 8,    "B-": 7,
    "CCC+": 6,  "CCC": 5,  "CCC-": 4,
    "CC": 3,    "C": 2,
    "SD": 1, "D": 1
}

rating_num_to_letter = {
    22:"AAA", 21:"AA+", 20:"AA", 19:"AA-",
    18:"A+", 17:"A", 16:"A-",
    15:"BBB+", 14:"BBB", 13:"BBB-",
    12:"BB+", 11:"BB", 10:"BB-",
    9:"B+", 8:"B", 7:"B-",
    6:"CCC+", 5:"CCC", 4:"CCC-",
    3:"CC", 2:"C", 1:"SD/D"
}

moody_to_sp = {
    "Aaa":"AAA", "Aa1":"AA+", "Aa2":"AA", "Aa3":"AA-",
    "A1":"A+", "A2":"A", "A3":"A-",
    "Baa1":"BBB+", "Baa2":"BBB", "Baa3":"BBB-",
    "Ba1":"BB+", "Ba2":"BB", "Ba3":"BB-",
    "B1":"B+", "B2":"B", "B3":"B-",
    "Caa1":"CCC+", "Caa2":"CCC", "Caa3":"CCC-",
    "Ca":"CC", "C":"C"
}

# ============================================================
# 2. Convertir chaque ligne -> notation S&P numérique
# ============================================================

def convert_to_sp(row):
    agency = row["Agency"]
    rating = str(row["Rating"]).strip()

    # S&P ou Fitch : même notation
    if agency in ["S&P", "SP", "Standard & Poor's", "Fitch"]:
        return rating_letter_to_num.get(rating)

    # Moody's
    if agency in ["Moody's", "Moodys", "Moody"]:
        sp_equiv = moody_to_sp.get(rating)
        if sp_equiv:
            return rating_letter_to_num.get(sp_equiv)

    return np.nan

df["rating_SP"] = df.apply(convert_to_sp, axis=1)

df = df.dropna(subset=["rating_SP"])

# ============================================================
# 3. Prendre la pire note de l’année par pays
# ============================================================

df_year = (
    df.groupby(["Code", "Year"], as_index=False)["rating_SP"]
      .min()        # pire note
)

# ============================================================
# 4. Groupes de pays demandés
# ============================================================

groups = [
    ["ARG", "FRA", "USA", "GBR", "JPN"],
    ["VNM", "EGY", "ECU", "ZAF", "GRC"]
]

# ============================================================
# 5. Graphiques
# ============================================================

for idx, group in enumerate(groups, start=1):
    df_g = df_year[df_year["Code"].isin(group)]

    plt.figure(figsize=(12, 6))

    for code in group:
        df_c = df_g[df_g["Code"] == code].sort_values("Year")
        if not df_c.empty:
            plt.plot(df_c["Year"], df_c["rating_SP"], marker="o", label=code)

    # Échelle complète S&P AAA → SD/D
    yvals = sorted(rating_num_to_letter.keys())
    plt.yticks(yvals, [rating_num_to_letter[y] for y in yvals])

    plt.title(f"Évolution rating S&P – Groupe {idx} : {', '.join(group)}")
    plt.xlabel("Année")
    plt.ylabel("Notation (S&P)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    output_png = os.path.join(BASE_DIR, f"ratings_SP_groupe_{idx}.png")
    plt.savefig(output_png, dpi=300)
    plt.close()

print("Graphiques générés avec succès ✔")
