"""
model_OLS_two_models.py

Ce script :
  - charge le DataFrame final (model_dataset.xlsx) déjà construit par ton modèle économétrique,
  - construit si besoin :
        * Deficit (% of GDP) = - Net lending/borrowing (% of GDP)
        * default_ever = 1 si le pays a déjà fait défaut au moins une fois dans l'histoire,
  - estime deux modèles OLS :

    (1) OLS SANS AUCUNE INDICATRICE :
        Rating_it = β0 + β1*Croissance + β2*Dette + β3*Intérêts + β4*Déficit
                     + β5*Inflation + β6*CompteCourant + ε_it

    (2) OLS AVEC is_em ET default_ever :
        Rating_it = β0 + β1*Croissance + β2*Dette + β3*Intérêts + β4*Déficit
                     + β5*Inflation + β6*CompteCourant
                     + β7*is_em_i + β8*default_ever_i + ε_it
"""

import pandas as pd
import statsmodels.api as sm


# Data déja done 
DATA_PATH = "model_dataset.xlsx"  # généré par ton script Modéle économétrique


def load_df_model(path: str = DATA_PATH) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    print("✔️ DataFrame chargé depuis :", path)
    print("Shape :", df.shape)
    print("Colonnes disponibles :", list(df.columns), "\n")

    # 1) Construire 'Deficit (% of GDP)' si absent
    #    Net lending/borrowing > 0 = surplus, < 0 = déficit
    if "Deficit (% of GDP)" not in df.columns and "Net lending/borrowing (% of GDP)" in df.columns:
        df["Deficit (% of GDP)"] = -df["Net lending/borrowing (% of GDP)"]
        print("→ Colonne 'Deficit (% of GDP)' construite à partir de 'Net lending/borrowing (% of GDP)'.\n")

    if "default_dummy" in df.columns and "default_ever" not in df.columns:
        df["default_ever"] = (
            df.sort_values(["Code", "Year"])
              .groupby("Code")["default_dummy"]
              .transform(lambda s: s.cummax())
              .astype(int)
        )
        print("→ Colonne 'default_ever' construite (1 si le pays a déjà fait défaut au moins une fois).\n")

    return df



# Modéle 1: OLS sans indicatrices
def ols_without_indicators(df: pd.DataFrame):
    """
    Rating_it = β0
                + β1 * GDPgrowth_it
                + β2 * Debtpib_it
                + β3 * Interest_it
                + β4 * Deficit_it
                + β5 * Inflation_it
                + β6 * CAB_it
                + ε_it
    """

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
        # Check si tt les colonnes dans le df
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


# Modéle 2 : OLS avec is_em et default_ever
def ols_with_isem_and_default_history(df: pd.DataFrame):
    """
    Rating_it = β0
                + β1 * GDPgrowth_it
                + β2 * Debtpib_it
                + β3 * Interest_it
                + β4 * Deficit_it
                + β5 * Inflation_it
                + β6 * CAB_it
                + β7 * is_em_i
                + β8 * default_ever_i
                + ε_it
      - is_em_i = 1 si le pays i est un pays émergent, 0 sinon
      - default_ever_i = 1 si le pays i a déjà fait défaut au moins une fois (sur toute l'histoire)
    """

    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "is_em", # dummy 1
        "default_ever", # dummy 2
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


# Prédiction
if __name__ == "__main__":
    df_model = load_df_model(DATA_PATH)
# estimer Model 1
    res_ols_no_indic = ols_without_indicators(df_model)

# estimer Model 2
    res_ols_with_indic = ols_with_isem_and_default_history(df_model)


    model_for_prediction = res_ols_with_indic   # modèle 2

    X_new = {
        "GDP growth (annual %)": 3.108,
        "Debt (% of GDP)": 68.7,
        "Interest payments (% of GDP)": 6.37,
        "Deficit (% of GDP)": 3.2,
        "Inflation, consumer prices (annual %)": 5.8,
        "Current account balance (% of GDP)": -3.0,
        "is_em": 0,
        "default_ever": 0,
    }

    X_new_df = pd.DataFrame([X_new])

    # IMPORTANT : ajouter la constante
    X_new_df = sm.add_constant(X_new_df, has_constant='add')

    print("\nColonnes X_new_df :", X_new_df.columns)
    print("Colonnes modèle :", model_for_prediction.params.index)

    y_pred = model_for_prediction.predict(X_new_df)

    print("\n===============================")
    print("   EXEMPLE DE PRÉDICTION")
    print("===============================")
    print("Rating prédit (score numérique) :", float(y_pred.values[0]))
