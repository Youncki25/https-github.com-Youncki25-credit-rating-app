"""
model_OLS_two_models_ar1.py

Ce script :
  - charge le DataFrame final (model_dataset.xlsx),
  - construit si besoin :
        * Deficit (% of GDP)
        * default_ever
        * rating_mean_num_lag1 (AR(1) sur la note moyenne, par pays)
  - estime deux modèles OLS :

    (1) OLS SANS INDICATRICES, AVEC AR(1) SUR LA NOTE (lag de rating_mean_num)
    (2) OLS AVEC is_em ET default_ever, AVEC AR(1) SUR LA NOTE

  - puis :
    * teste le modèle 1 (sans indicatrices) sur la DERNIÈRE ANNÉE DISPONIBLE :
        - récupère les vraies variables macro + lag de la note,
        - prédit avec le modèle,
        - compare au rating moyen observé (rating_mean_num).
"""

import pandas as pd
import statsmodels.api as sm


# ============================
# 0) Chemin des données
# ============================

DATA_PATH = "model_dataset.xlsx"


# ============================
# 1) Chargement et préparation du DataFrame
# ============================

def load_df_model(path: str = DATA_PATH) -> pd.DataFrame:
    """
    Charge le DataFrame du modèle et construit, si besoin :
      - Deficit (% of GDP)
      - default_ever
      - rating_mean_num_lag1 (AR(1) par pays)
    """
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    print("✔️ DataFrame chargé depuis :", path)
    print("Shape :", df.shape)
    print("Colonnes disponibles :", list(df.columns), "\n")

    # Deficit si manquant
    if "Deficit (% of GDP)" not in df.columns and \
       "Net lending/borrowing (% of GDP)" in df.columns:
        df["Deficit (% of GDP)"] = -df["Net lending/borrowing (% of GDP)"]
        print("→ Colonne 'Deficit (% of GDP)' construite.\n")

    # default_ever si manquant
    if "default_dummy" in df.columns and "default_ever" not in df.columns:
        df = df.sort_values(["Code", "Year"])
        df["default_ever"] = (
            df.groupby("Code")["default_dummy"]
              .transform(lambda s: s.cummax())
              .astype(int)
        )
        print("→ Colonne 'default_ever' construite.\n")
    else:
        df = df.sort_values(["Code", "Year"])

    # === AR(1) sur la note : lag de rating_mean_num par pays ===
    if "rating_mean_num" not in df.columns:
        raise ValueError("La colonne 'rating_mean_num' est manquante dans le DataFrame.")

    df["rating_mean_num_lag1"] = (
        df.sort_values(["Code", "Year"])
          .groupby("Code")["rating_mean_num"]
          .shift(1)
    )
    print("→ Colonne 'rating_mean_num_lag1' (lag 1 par Code) construite.\n")

    return df


# ============================
# 2) Modèle 1 : OLS sans indicatrices, avec AR(1)
# ============================

def ols_without_indicators(df: pd.DataFrame):
    """
    Modèle OLS sans variables indicatrices (pas de is_em, pas de default_ever),
    mais avec AR(1) via rating_mean_num_lag1.
    """
    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "rating_mean_num_lag1",
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
    print("   MODÈLE 1 : OLS SANS INDICATRICES (AR(1) via lag de la note)")
    print("===============================\n")
    print(model.summary())

    return model


# ============================
# 3) Modèle 2 : OLS avec is_em + default_ever + AR(1)
# ============================

def ols_with_isem_and_default_history(df: pd.DataFrame):
    """
    Modèle OLS avec variables indicatrices, + AR(1).
    """
    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "Control of Corruption",
        "is_em",
        "default_ever",
        "rating_mean_num_lag1",
    ]

    missing = [c for c in X_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    df_clean = df.dropna(subset=X_cols + ["rating_mean_num"]).copy()

    X = df_clean[X_cols]
    y = df_clean["rating_mean_num"]

    X = sm.add_constant(X)

    model = sm.OLS(y, X).fit()

    print("\n===============================")
    print("   MODÈLE 2 : OLS AVEC is_em + default_ever (AR(1))")
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

    # 🔎 On utilise le modèle SANS indicatrices pour prédire la dernière année
    model_for_prediction = res_ols_no_indic

    # Variables du modèle 1
    X_cols_test = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "rating_mean_num_lag1",
    ]

    df_complete = df_model.dropna(subset=X_cols_test + ["rating_mean_num", "Year"]).copy()

    if df_complete.empty:
        print("\n⚠️ Aucune observation complète pour le test sur la dernière année.")
    else:
        latest_year = int(df_complete["Year"].max())
        df_last = df_complete[df_complete["Year"] == latest_year].copy()

        if df_last.empty:
            print(f"\n⚠️ Aucune observation pour l'année {latest_year}.")
        else:
            X_last = df_last[X_cols_test]
            X_last = sm.add_constant(X_last, has_constant='add')

            y_last_pred = model_for_prediction.predict(X_last)

            df_last["rating_pred"] = y_last_pred
            df_last["error"] = df_last["rating_pred"] - df_last["rating_mean_num"]

            print("\n===============================")
            print("   TEST SUR LA DERNIÈRE ANNÉE DISPONIBLE (MODÈLE SANS INDICATRICES)")
            print("===============================")
            print(f"Année testée : {latest_year}\n")

            print(
                df_last[["Code", "Year", "rating_mean_num", "rating_pred", "error"]]
                .sort_values("Code")
            )

            mae = df_last["error"].abs().mean()
            print(f"\nMAE (erreur absolue moyenne) sur {latest_year} : {mae:.3f}")
