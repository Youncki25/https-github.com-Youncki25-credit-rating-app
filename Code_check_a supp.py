import pandas as pd

# Charger ton fichier Ratings
df = pd.read_excel("Ratings.xlsx")

# Normaliser colonnes si nécessaire
df.columns = [c.strip() for c in df.columns]

# On garde uniquement l'essentiel
cols = ["Year", "Code", "rating_mean_num"]

df_clean = df[cols].drop_duplicates().sort_values(["Code", "Year"])

print(df_clean)
df_clean.to_excel("ratings_mean_clean.xlsx", index=False)
