# Modéle économétrique
#MG : Ratings
# Inès : Défaut , VBA for each ---> mettre 0 si pas de défaut et 1 si défaut
# Conitnue  Modélé éconoémtrique
#yt=B0+B1PIB+B2INF+B3FISCAL_BALANCE+B4UNEMPLOYMENT+B5INTEREST_PAYMENTS+B6TAX_REVENUE +B7DUMMY_DEFAULT_PREVIOUS+B8DUMMY_DEVELOPED_COUNTRY +B9RATINGS +e
import pandas as pd
import numpy as np
from statsmodels.miscmodels.ordinal_model import OrderedModel
# pour la transformation linéaire
rating_to_score_sp_fitch = {
    "AAA": 21, "AA+": 20, "AA": 19, "AA-": 18,
    "A+": 17, "A": 16, "A-": 15,
    "BBB+": 14, "BBB": 13, "BBB-": 12,
    "BB+": 11, "BB": 10, "BB-": 9,
    "B+": 8, "B": 7, "B-": 6,
    "CCC+": 5, "CCC": 4, "CCC-": 3,
    "CC": 2, "C": 1, "D": 1
}
rating_to_score_moodys = {
    "Aaa": 21,
    "Aa1": 20, "Aa2": 19, "Aa3": 18,
    "A1": 17, "A2": 16, "A3": 15,
    "Baa1": 14, "Baa2": 13, "Baa3": 12,
    "Ba1": 11, "Ba2": 10, "Ba3": 9,
    "B1": 8, "B2": 7, "B3": 6,
    "Caa1": 5, "Caa2": 4, "Caa3": 3,
    "Ca": 2, "C": 1
}
# Inversion des dictionnaires pour la conversion inverse
score_to_rating_sp = {v: k for k, v in rating_to_score_sp_fitch.items()}

#fonction de conversion
def sp_fitch_to_score(r):
    return rating_to_score_sp_fitch.get(r, np.nan)
def moodys_to_score(r):
    return rating_to_score_moodys.get(r, np.nan)
# Data 
df = pd.read_csv("")
df["score_sp"] = df["rating_sp"].apply(sp_fitch_to_score)
df["score_fitch"] = df["rating_fitch"].apply(sp_fitch_to_score)
df["score_moodys"] = df["rating_moodys"].apply(moodys_to_score)
df["score_mean"] = df[["score_sp", "score_fitch", "score_moodys"]].mean(axis=1)
df["score_mean_cat"] = df["score_mean"].round().astype("Int64")
#Modèle
# On enlève les lignes où le rating est manquant
df_model = df.dropna(subset=["score_mean_cat"]).copy()
y = df_model["score_mean_cat"]
# définir les variable explicatives
X = df_model[["gdp_growth", "debt_gdp", "inflation", "current_account", "is_em"]]
#Modéle ordinal
model = OrderedModel(
    y,
    X,
    distr="logit"  # ou "probit" selon ce que on veut (voir les papiers)
)
result = model.fit(method="bfgs")
print(result.summary())