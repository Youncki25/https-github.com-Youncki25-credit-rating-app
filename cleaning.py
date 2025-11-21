import pandas as pd

df = pd.read_excel("/Users/beldjenna/Desktop/Rating Algo/Rating_API.xlsx")

# --- 0) Supprimer NR car impossibles à convertir ---
df = df[df["Rating"] != "NR"]

# --- 1) Convert qualitative ratings to numeric ---
rating_to_num = {
    "AAA":22, "AA+":21, "AA":20, "AA-":19,
    "A+":18, "A":17, "A-":16,
    "BBB+":15, "BBB":14, "BBB-":13,
    "BB+":12, "BB":11, "BB-":10,
    "B+":9, "B":8, "B-":7,
    "CCC+":6, "CCC":5, "CCC-":4,
    "CC":3, "C":2, "SD":1, "D":1
}

df["rating_num"] = df["Rating"].map(rating_to_num)

# --- 2) Keep last month of the year for each country & agency ---
df_sorted = df.sort_values(["Country","Agency","Year","Month"])
idx = df_sorted.groupby(["Country","Agency","Year"])["Month"].idxmax()
df_last = df_sorted.loc[idx]

# --- 3) Compute MEAN rating across agencies ---
df_mean = df_last.groupby(["Country","Code","Year"],as_index=False).agg(
    rating_mean_num=("rating_num","mean")
)

# --- 4) Convert mean numeric → qualitative ---
num_to_rating = {v:k for k,v in rating_to_num.items()}

df_mean["rating_mean_qualitative"] = (
    df_mean["rating_mean_num"]
    .round()
    .astype("Int64")   # <-- accepte NA !
    .map(num_to_rating)
)

# --- 5) Detect missing (Country,Year) ---
years = range(df_mean["Year"].min(), df_mean["Year"].max()+1)
countries = df_mean[["Country","Code"]].drop_duplicates()

full = countries.merge(pd.DataFrame({"Year":years}), how="cross")
merged = full.merge(df_mean, on=["Country","Code","Year"], how="left")

missing = merged[merged["rating_mean_num"].isna()][["Country","Code","Year"]]

# --- EXPORT ---
df_mean.to_excel("/Users/beldjenna/Desktop/Rating Algo/rating_mean_by_country.xlsx", index=False)
missing.to_excel("/Users/beldjenna/Desktop/Rating Algo/missing_ratings.xlsx", index=False)

print("Fichiers exportés.")
