import pandas as pd
import matplotlib.pyplot as plt

# =========================
# 1. Charger les données
# =========================
df = pd.read_excel("/Users/beldjenna/Desktop/Rating Algo/Rating_API.xlsx")
df.columns = [c.strip() for c in df.columns]

# On garde seulement les pays qui t'intéressent
selected_codes = ["ARG", "FRA", "USA", "GBR", "JPN",
                  "VNM", "EGY", "ECU", "ZAF", "GRC"]

df = df[df["Code"].isin(selected_codes)].copy()

# On enlève les éventuels NaN sur rating_mean_num
df = df.dropna(subset=["rating_mean_num"])

# =========================
# 2. Passer à une fréquence annuelle
#    -> 1 ligne par Code / Year
# =========================
df_year = (
    df.groupby(["Code", "Year"], as_index=False)
      ["rating_mean_num"].mean()
)

# =========================
# 3. Préparer les groupes de 5 pays
# =========================
groups = [
    ["ARG", "FRA", "USA", "GBR", "JPN"],
    ["VNM", "EGY", "ECU", "ZAF", "GRC"]
]

# Mapping rating numérique -> lettre
rating_map = {
    22: "AAA", 21: "AA+", 20: "AA", 19: "AA-",
    18: "A+", 17: "A", 16: "A-",
    15: "BBB+", 14: "BBB", 13: "BBB-",
    12: "BB+", 11: "BB", 10: "BB-",
    9: "B+", 8: "B", 7: "B-",
    6: "CCC+", 5: "CCC", 4: "CCC-",
    3: "CC", 2: "C", 1: "SD/D"
}

# =========================
# 4. Graphiques : 1 figure par groupe de 5 pays
# =========================
for idx, group in enumerate(groups, start=1):
    df_group = df_year[df_year["Code"].isin(group)].copy()

    plt.figure(figsize=(10, 6))

    for code in group:
        df_country = (
            df_group[df_group["Code"] == code]
            .sort_values("Year")
        )
        if df_country.empty:
            continue

        plt.plot(
            df_country["Year"],
            df_country["rating_mean_num"],
            marker="o",
            linestyle="-",
            label=code
        )

    plt.title(f"Évolution du rating moyen – Groupe {idx} : {', '.join(group)}")
    plt.xlabel("Année")
    plt.ylabel("Notation moyenne")

    # ----- Axe Y en lettres (AAA, AA-, etc.) -----
    if not df_group.empty:
        ymin = int(round(df_group["rating_mean_num"].min()))
        ymax = int(round(df_group["rating_mean_num"].max()))
        y_ticks = list(range(ymin, ymax + 1))
        plt.yticks(y_ticks, [rating_map.get(y, "") for y in y_ticks])

    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    # Sauvegarde image
    plt.savefig(f"ratings_selected_groupe_{idx}.png", dpi=300)
    plt.close()

import pandas as pd

# =========================
# 1. Charger le fichier
# =========================
df = pd.read_excel("/Users/beldjenna/Desktop/Rating Algo/Rating_API.xlsx")
df.columns = [c.strip() for c in df.columns]

# On garde les pays voulus
selected_codes = ["ARG", "FRA", "USA", "GBR", "JPN",
                  "VNM", "EGY", "ECU", "ZAF", "GRC"]

df = df[df["Code"].isin(selected_codes)].copy()

# =========================
# 2. Annualiser (1 valeur par pays + année)
# =========================
df_year = (
    df.groupby(["Code", "Year"], as_index=False)["rating_mean_num"]
      .mean()
)

# =========================
# 3. Tableau de statistiques
# =========================
stats = df_year.groupby("Code")["rating_mean_num"].agg(
    min_rating   = "min",
    max_rating   = "max",
    mean_rating  = "mean",
    median_rating= "median",
    std_rating   = "std",
    n_years      = "count"
)

# Arrondir proprement
stats = stats.round(2)

print(stats)

# Export Excel si tu veux
stats.to_excel("/Users/beldjenna/Desktop/Rating Algo/stats_descriptives_ratings.xlsx")
