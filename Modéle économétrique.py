import os
import glob
import numpy as np
import pandas as pd
from statsmodels.miscmodels.ordinal_model import OrderedModel

# ================================
# 1) LECTURE DES DONNÉES WB
# ================================

WB_INDICATORS_CANON = [
    "GDP growth (annual %)", 
    "GDP per capita (current US$)",
    "Inflation, consumer prices (annual %)",
    "Trade openness (% of GDP)",
    "Debt (% of GDP)",
    "Net lending/borrowing (% of GDP)",
    "Current account balance (% of GDP)",
    "Interest payments (% of GDP)",
    "Control of Corruption",
    "Political Stability and Absence of Violence",
]

def _standardize_wb_columns(df: pd.DataFrame, file_path: str | None = None) -> pd.DataFrame:
    fname = os.path.basename(file_path) if file_path else "WB_file"
    print(f"   Colonnes brutes WB ({fname}) : {list(df.columns)}")

    # Détection colonne année
    year_col = None
    for cand in ["Year", "year", "YEAR", "date", "Date", "DATE"]:
        if cand in df.columns:
            year_col = cand
            break

    if year_col is None:
        for c in df.columns:
            if "Unnamed" in str(c):
                year_col = c
                break

    if year_col is None:
        raise ValueError(f"Impossible de trouver la colonne année dans {fname}.")

    if year_col != "Year":
        print(f"   → Colonne année détectée '{year_col}', renommée en 'Year'")
        df = df.rename(columns={year_col: "Year"})

    if not np.issubdtype(df["Year"].dtype, np.number):
        year_conv = pd.to_datetime(df["Year"], errors="coerce")
        if year_conv.notna().any():
            df["Year"] = year_conv.dt.year
        else:
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    df = df[~df["Year"].isna()].copy()
    df["Year"] = df["Year"].astype(int)

    rename_map = {
        "Currrent account balance (% of GDP)": "Current account balance (% of GDP)",
        "Current account balancce (% of GDP)": "Current account balance (% of GDP)",
        "Control of Corruptioon": "Control of Corruption",
    }
    df = df.rename(columns=rename_map)

    cols_to_keep = ["Year"] + [col for col in WB_INDICATORS_CANON if col in df.columns]
    print(f"   → Colonnes retenues ({fname}) : {cols_to_keep}")

    return df[cols_to_keep].copy()


def load_wb_panel(base_dir: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 1) LECTURE DES DONNÉES WB")
    print("===============================")

    files = glob.glob(os.path.join(base_dir, "*_WB_timeseries.xlsx"))
    print(f"→ Fichiers WB détectés : {files}\n")

    all_list = []
    for path in files:
        print(f"→ Lecture fichier WB : {path}")
        df_raw = pd.read_excel(path)
        df = _standardize_wb_columns(df_raw, file_path=path)
        code = os.path.basename(path).split("_")[0]
        df["Code"] = code
        df["Country"] = code
        all_list.append(df)
        print("   ✔️ Lecture OK\n")

    wb_panel = pd.concat(all_list, ignore_index=True)
    print(f"✔️ WB Panel construit. Shape : {wb_panel.shape}\n")
    return wb_panel


# ================================
# 2) LECTURE DES RATINGS
# ================================

def load_ratings(base_dir: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 2) LECTURE DES RATINGS")
    print("===============================")

    path = os.path.join(base_dir, "Ratings.xlsx")
    df = pd.read_excel(path)
    df_mean = df.groupby(["Country", "Code", "Year"], as_index=False)["rating_mean_num"].mean()
    print("✔️ Ratings chargés\n")
    return df_mean


# ================================
# 3) LECTURE DES DONNÉES DE DÉFAUT
# ================================

def load_defaults(path: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 3) LECTURE DES DÉFAUTS")
    print("===============================")

    df_def = pd.read_excel(path)
    if "Year" not in df_def.columns:
        df_def = df_def.rename(columns={"Unnamed: 0": "Year"})

    df_def["Year"] = pd.to_numeric(df_def["Year"], errors="coerce")
    df_def = df_def.dropna(subset=["Year"])
    df_def["Year"] = df_def["Year"].astype(int)

    mapping = {
        "France": "FRA", "US": "USA", "Argentine": "ARG", "Grèce": "GRC",
        "équateur": "ECU", "Egypte": "EGY", "Japon": "JPN", "Vietnam": "VNM",
        "Afrique du Sud": "ZAF", "Angleterre": "GBR"
    }

    keep = ["Year"]
    for col in df_def.columns:
        if col in mapping:
            df_def[mapping[col]] = df_def[col]
            keep.append(mapping[col])

    df_def = df_def[keep]
    df_long = df_def.melt(id_vars=["Year"], var_name="Code", value_name="default_dummy")
    df_long["default_dummy"] = df_long["default_dummy"].fillna(0).astype(int)

    print("✔️ Defaults chargés\n")
    return df_long


# ================================
# 4) CONSTRUCTION DU DATASET FINAL
# ================================

def build_model_dataset(base_dir: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 4) CONSTRUCTION DU DATASET FINAL")
    print("===============================")

    wb_panel = load_wb_panel(base_dir)
    ratings = load_ratings(base_dir)
    defaults = load_defaults(os.path.join(base_dir, "Crédit_rating.xlsm"))

    # Merge
    df = wb_panel.merge(ratings, on=["Code", "Year"], how="left")
    df = df.merge(defaults, on=["Code", "Year"], how="left")
    df["default_dummy"] = df["default_dummy"].fillna(0).astype(int)

    # EM
    EM = {"ARG", "ECU", "EGY", "VNM", "ZAF"}
    df["is_em"] = df["Code"].isin(EM).astype(int)

    # Lag défaut
    df = df.sort_values(["Code", "Year"])
    df["default_lag"] = df.groupby("Code")["default_dummy"].shift(1).fillna(0).astype(int)

    # Imputation NA
    macro_cols = [
        "GDP growth (annual %)", "GDP per capita (current US$)",
        "Inflation, consumer prices (annual %)", "Trade openness (% of GDP)",
        "Net lending/borrowing (% of GDP)", "Current account balance (% of GDP)",
        "Debt (% of GDP)", "Interest payments (% of GDP)"
    ]
    gouv_cols = ["Control of Corruption", "Political Stability and Absence of Violence"]

    df[macro_cols] = df.groupby("Code")[macro_cols].transform(
        lambda g: g.interpolate().bfill().ffill()
    )
    df[gouv_cols] = df.groupby("Code")[gouv_cols].transform(
        lambda g: g.bfill().ffill()
    )

    df["Deficit (% of GDP)"] = -df["Net lending/borrowing (% of GDP)"]
    df["score_mean_cat"] = df["rating_mean_num"].round().astype("Int64")

    X_cols = [
        "GDP growth (annual %)", "Debt (% of GDP)", "Interest payments (% of GDP)",
        "Deficit (% of GDP)", "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)", "is_em", "default_lag"
    ]

    df_model = df.dropna(subset=X_cols + ["score_mean_cat"]).copy()

    # ✅ SAUVEGARDE AUTOMATIQUE DU DATAFRAME FINAL
    out_path = os.path.join(base_dir, "model_dataset.xlsx")
    df_model.to_excel(out_path, index=False)
    print(f"✔️ Dataset final sauvegardé → {out_path}\n")

    return df_model


# ================================
# 5) ESTIMATION
# ================================

def estimate_ordered_model(base_dir: str):
    df_model = build_model_dataset(base_dir)

    X_cols = [
        "GDP growth (annual %)", "Debt (% of GDP)", "Interest payments (% of GDP)",
        "Deficit (% of GDP)", "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)", "is_em", "default_lag"
    ]

    y = df_model["score_mean_cat"].astype(int)
    X = df_model[X_cols]

    model = OrderedModel(y, X, distr="logit")
    result = model.fit(method="bfgs", disp=True)

    print(result.summary())
    return result, df_model, X_cols


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    result, df_model, X_cols = estimate_ordered_model(base_dir)

    # ===============================
    # 6) EXEMPLE DE PRÉDICTION AVEC LE MODÈLE ORDINAL
    # ===============================

    # Exemple de vecteur de caractéristiques (à adapter à ton pays / année)
    X_new = {
        "GDP growth (annual %)": 0.725,
        "Debt (% of GDP)": 134.6,
        "Interest payments (% of GDP)": 5.0,
        "Deficit (% of GDP)": 4.1,
        "Inflation, consumer prices (annual %)": 0.98,
        "Current account balance (% of GDP)": -3.0,
        "is_em": 0,         # 0 = DM, 1 = EM
        "default_lag": 0,   # défaut l'année précédente
    }

    # Construire un DataFrame avec exactement les colonnes X_cols
    X_new_df = pd.DataFrame([X_new])[X_cols]

    # Probabilités par catégorie
probs = result.model.predict(result.params, exog=X_new_df, which="prob")

# Récupérer les catégories possibles
categories = np.sort(df_model["score_mean_cat"].dropna().unique())

# Catégorie la plus probable
idx_max = int(np.argmax(probs[0]))
predicted_cat = int(categories[idx_max])

# Score attendu (espérance)
expected_score = float((probs[0] * categories).sum())

print("\n===============================")
print("   PRÉDICTION AVEC LE MODÈLE ORDINAL")
print("===============================")
print("Probabilités par catégorie (dans l'ordre des catégories) :")
for c, p in zip(categories, probs[0]):
    print(f"  P(score = {int(c)}) = {p:.4f}")
print(f"\nCatégorie la plus probable      : {predicted_cat}")
print(f"Score attendu (valeur moyenne)  : {expected_score:.2f}")
