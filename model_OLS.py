"""
model_OLS_two_models.py

Ce script :
  - charge le DataFrame final (model_dataset.xlsx),
  - construit si besoin :
        * Deficit (% of GDP)
        * default_ever
  - estime deux modèles OLS :

    (1) OLS SANS AUCUNE INDICATRICE
    (2) OLS AVEC is_em ET default_ever

  - puis :
    * teste le modèle 2 sur la DERNIÈRE ANNÉE DISPONIBLE :
        - récupère les vraies variables macro + dummies,
        - prédit avec le modèle,
        - compare au rating moyen observé (rating_mean_num).
"""

import pandas as pd
import statsmodels.api as sm


# ============================
# 0) Chemin des données
# ============================

DATA_PATH = "model_dataset.xlsx"
# ou, si besoin :
# DATA_PATH = r"C:\Users\youne\https-github.com-Youncki25-credit-rating-app\model_dataset.xlsx"


# ============================
# 1) Chargement et préparation du DataFrame
# ============================

def load_df_model(path: str = DATA_PATH) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    print("✔️ DataFrame chargé depuis :", path)
    print("Shape :", df.shape)
    print("Colonnes disponibles :", list(df.columns), "\n")

    # Deficit si manquant
    if "Deficit (% of GDP)" not in df.columns and "Net lending/borrowing (% of GDP)" in df.columns:
        df["Deficit (% of GDP)"] = -df["Net lending/borrowing (% of GDP)"]
        print("→ Colonne 'Deficit (% of GDP)' construite.\n")

    # default_ever si manquant
    if "default_dummy" in df.columns and "default_ever" not in df.columns:
        df["default_ever"] = (
            df.sort_values(["Code", "Year"])
              .groupby("Code")["default_dummy"]
              .transform(lambda s: s.cummax())
              .astype(int)
        )
        print("→ Colonne 'default_ever' construite.\n")

    return df


# ============================
# 2) Modèle 1 : OLS sans indicatrices
# ============================

def ols_without_indicators(df: pd.DataFrame):
    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
    ]

    missing = [c for c in X_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes pour le modèle OLS sans indicatrices : {missing}")

    df_clean = df.dropna(subset=X_cols + ["rating_mean_num"]).copy()

    X = df_clean[X_cols]
    y = df_clean["rating_mean_num"]

    X = sm.add_constant(X)

    model = sm.OLS(y, X).fit()

    print("\n===============================")
    print("   MODÈLE 1 : OLS SANS INDICATRICES")
    print("===============================\n")
    print(model.summary())

    return model


# ============================
# 3) Modèle 2 : OLS avec is_em + default_ever
# ============================

def ols_with_isem_and_default_history(df: pd.DataFrame):
    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "is_em",
        "default_ever",
    ]

    missing = [c for c in X_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes pour le modèle OLS avec is_em + default_ever : {missing}")

    df_clean = df.dropna(subset=X_cols + ["rating_mean_num"]).copy()

    X = df_clean[X_cols]
    y = df_clean["rating_mean_num"]

    X = sm.add_constant(X)

    model = sm.OLS(y, X).fit()

    print("\n===============================")
    print("   MODÈLE 2 : OLS AVEC is_em + default_ever")
    print("===============================\n")
    print(model.summary())

    return model


# ============================
# 4) MAIN + TEST DERNIÈRE ANNÉE
# ============================

if __name__ == "__main__":
    # 1) Charger data
    df_model = load_df_model(DATA_PATH)

    # 2) Estimer modèles
    res_ols_no_indic = ols_without_indicators(df_model)
    res_ols_with_indic = ols_with_isem_and_default_history(df_model)

    # On utilise le modèle 2 pour tester
    model_for_prediction =  res_ols_no_indic

    # 3) Test sur la dernière année dispo
    X_cols_ols2 = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        #"is_em",
        #"default_ever",
    ]

    df_complete = df_model.dropna(subset=X_cols_ols2 + ["rating_mean_num", "Year"]).copy()

    if df_complete.empty:
        print("\n⚠️ Aucune observation complète pour le test sur la dernière année.")
    else:
        latest_year = int(df_complete["Year"].max())
        df_last = df_complete[df_complete["Year"] == latest_year].copy()

        if df_last.empty:
            print(f"\n⚠️ Aucune observation pour l'année {latest_year}.")
        else:
            X_last = df_last[X_cols_ols2]
            X_last = sm.add_constant(X_last, has_constant='add')

            y_last_pred = model_for_prediction.predict(X_last)

            df_last["rating_pred"] = y_last_pred
            df_last["error"] = df_last["rating_pred"] - df_last["rating_mean_num"]
            print("   TEST SUR LA DERNIÈRE ANNÉE DISPONIBLE")
            print("===============================")
            print(f"Année testée : {latest_year}\n")

            print(
                df_last[["Code", "Year", "rating_mean_num", "rating_pred", "error"]]
                .sort_values("Code")
                .head(50)  # tu peux enlever .head si tu veux tout
            )

            mae = df_last["error"].abs().mean()
            print(f"\nMAE (erreur absolue moyenne) sur {latest_year} : {mae:.3f}")
