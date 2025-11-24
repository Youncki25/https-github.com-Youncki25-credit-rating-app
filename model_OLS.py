"""
model_OLS_two_models_ar1.py

Ce script :
  - charge le DataFrame final (model_dataset.xlsx),
  - construit si besoin :
        * Deficit (% of GDP)
        * default_ever
        * rating_mean_num_lag1 (AR(1) sur la note moyenne, par pays)
  - estime deux modèles OLS :

    (1) OLS SANS INDICATRICES, AVEC AR(1) SUR LA NOTE
    (2) OLS AVEC is_em ET default_ever, AVEC AR(1) SUR LA NOTE  (mais on ne l'affiche plus)

  - puis :
    * teste le modèle 1 (sans indicatrices) sur la DERNIÈRE ANNÉE DISPONIBLE
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
    Charge le DataFrame et construit :
      - Deficit (% of GDP)
      - default_ever
      - rating_mean_num_lag1
    """
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    print("✔️ DataFrame chargé depuis :", path)
    print("Shape :", df.shape)
    print("Colonnes disponibles :", list(df.columns), "\n")

    # Construction Deficit si absent
    if "Deficit (% of GDP)" not in df.columns and \
       "Net lending/borrowing (% of GDP)" in df.columns:
        df["Deficit (% of GDP)"] = -df["Net lending/borrowing (% of GDP)"]
        print("→ Colonne 'Deficit (% of GDP)' construite.\n")

    # default_ever si absent
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

    # AR(1) sur la note
    if "rating_mean_num" not in df.columns:
        raise ValueError("La colonne 'rating_mean_num' est manquante.")

    df["rating_mean_num_lag1"] = (
        df.sort_values(["Code", "Year"])
        .groupby("Code")["rating_mean_num"]
        .shift(1)
    )
    print("→ Colonne 'rating_mean_num_lag1' construite.\n")

    return df


# ============================
# 2) Modèle 1 : OLS sans indicatrices, avec AR(1)
# ============================

def ols_without_indicators(df: pd.DataFrame):
    """
    Modèle OLS sans dummies, avec AR(1)
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
        raise ValueError(f"Colonnes manquantes : {missing}")

    df_clean = df.dropna(subset=X_cols + ["rating_mean_num"]).copy()

    X = df_clean[X_cols]
    y = df_clean["rating_mean_num"]

    X = sm.add_constant(X)

    model = sm.OLS(y, X).fit()

    print("\n======================================")
    print("   MODÈLE 1 : OLS SANS INDICATRICES (AR(1))")
    print("======================================\n")
    print(model.summary())

    return model


# ============================
# 3) Modèle 2 : OLS AVEC dummies (AR(1)) — NON AFFICHÉ
# ============================

def ols_with_isem_and_default_history(df: pd.DataFrame):
    """
    Modèle OLS avec indicatrices, + AR(1)
    (résumé NON affiché)
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

    df_clean = df.dropna(subset=X_cols + ["rating_mean_num"]).copy()
    X = df_clean[X_cols]
    y = df_clean["rating_mean_num"]
    X = sm.add_constant(X)

    model = sm.OLS(y, X).fit()

    # ❌ On ne print PAS ce modèle
    return model


# ============================
# 4) MAIN + TEST dernière année
# ============================

if __name__ == "__main__":
    # 1) Data
    df_model = load_df_model(DATA_PATH)

    # 2) Modèles
    res_ols_no_indic = ols_without_indicators(df_model)
    res_ols_with_indic = ols_with_isem_and_default_history(df_model)  # silencieux

    # On utilise UNIQUEMENT le modèle sans indicatrices
    model_for_prediction = res_ols_no_indic

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
        print("\n⚠️ Aucune observation complète pour le test.")
    else:
        latest_year = int(df_complete["Year"].max())
        df_last = df_complete[df_complete["Year"] == latest_year].copy()

        if df_last.empty:
            print(f"⚠️ Aucune donnée pour {latest_year}.")
        else:
            X_last = sm.add_constant(df_last[X_cols_test], has_constant='add')
            y_last_pred = model_for_prediction.predict(X_last)

            df_last["rating_pred"] = y_last_pred
            df_last["error"] = df_last["rating_pred"] - df_last["rating_mean_num"]

            print("\n======================================")
            print("  TEST SUR LA DERNIÈRE ANNÉE (MODEL SANS INDICATRICES)")
            print("======================================")
            print(f"Année testée : {latest_year}\n")

            print(
                df_last[["Code", "Year", "rating_mean_num", "rating_pred", "error"]]
                .sort_values("Code")
            )

            mae = df_last["error"].abs().mean()
            print(f"\nMAE sur {latest_year} : {mae:.3f}")
