import os
import glob
import numpy as np
import pandas as pd
from statsmodels.miscmodels.ordinal_model import OrderedModel

# =======================================================================================
# 0) LISTE DES INDICATEURS WB
# =======================================================================================

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

# =======================================================================================
# 1) STANDARDISATION DES FICHIERS WB
# =======================================================================================

def _standardize_wb_columns(df: pd.DataFrame, file_path: str | None = None) -> pd.DataFrame:
    fname = os.path.basename(file_path) if file_path else "WB_file"
    print(f"   Colonnes brutes WB ({fname}) : {list(df.columns)}")

    # Trouver la colonne année
    year_col = None
    for cand in ["Year", "year", "YEAR", "date", "Date", "DATE"]:
        if cand in df.columns:
            year_col = cand
            break
    if year_col is None:
        # Excel foireux : années dans "Unnamed"
        for c in df.columns:
            if "Unnamed" in str(c):
                year_col = c
                break
    if year_col is None:
        raise ValueError(f"Impossible de trouver la colonne année dans {fname}.")

    if year_col != "Year":
        print(f"   → Colonne année détectée '{year_col}', renommée en 'Year'")
        df = df.rename(columns={year_col: "Year"})

    # Conversion de Year → entier
    if not np.issubdtype(df["Year"].dtype, np.number):
        year_conv = pd.to_datetime(df["Year"], errors="coerce")
        if year_conv.notna().any():
            df["Year"] = year_conv.dt.year
        else:
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    df = df.dropna(subset=["Year"]).copy()
    df["Year"] = df["Year"].astype(int)

    # Harmonisation noms
    rename_map = {
        "Currrent account balance (% of GDP)": "Current account balance (% of GDP)",
        "Current account balancce (% of GDP)": "Current account balance (% of GDP)",
        "Control of Corruptioon": "Control of Corruption",
    }
    df = df.rename(columns=rename_map)

    cols_to_keep = ["Year"] + [col for col in WB_INDICATORS_CANON if col in df.columns]
    print(f"   → Colonnes retenues ({fname}) : {cols_to_keep}")

    return df[cols_to_keep].copy()

# =======================================================================================
# 2) CHARGEMENT DU PANEL WB
# =======================================================================================

def load_wb_panel(base_dir: str) -> pd.DataFrame:
    print(" 1) LECTURE DES DONNÉES WB")

    files = glob.glob(os.path.join(base_dir, "*_WB_timeseries.xlsx"))
    print(f"→ Fichiers WB détectés : {files}\n")

    if not files:
        raise FileNotFoundError("Aucun fichier *_WB_timeseries.xlsx trouvé.")

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

# =======================================================================================
# 3) RATINGS — ANNUALISATION + COMPLETION
# =======================================================================================

def load_ratings(base_dir: str, wb_panel: pd.DataFrame) -> pd.DataFrame:
    print(" 2) LECTURE DES RATINGS")

    path = os.path.join(base_dir, "Rating_API.xlsx")
    print(f"→ Fichier utilisé : {path}")

    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    if "rating_mean_num" not in df.columns or "Year" not in df.columns:
        raise ValueError("Il faut au moins 'Year' et 'rating_mean_num' dans Rating_API.xlsx.")

    # Annualisation par moyenne
    df_year = (
        df.groupby(["Country", "Code", "Year"], as_index=False)["rating_mean_num"]
          .mean()
    )

    # On garde seulement codes présents dans WB
    wb_codes = wb_panel["Code"].unique()
    df_year = df_year[df_year["Code"].isin(wb_codes)].copy()

    # Compléter années manquantes → interpolation nearest
    def _fill_nearest(group):
        group = group.sort_values("Year")
        group = group.groupby("Year", as_index=True).agg({
            "rating_mean_num": "mean",
            "Code": "first",
            "Country": "first",
        })

        code = group["Code"].iloc[0]
        years = wb_panel[wb_panel["Code"] == code]["Year"]
        if years.empty:
            return group.reset_index()

        full_years = range(int(years.min()), int(years.max()) + 1)
        group = group.reindex(full_years)

        group["Code"] = code
        group["Country"] = group["Country"].dropna().iloc[0]
        group["rating_mean_num"] = group["rating_mean_num"].interpolate("nearest", limit_direction="both")
        group["Year"] = group.index
        return group.reset_index(drop=True)

    df_filled = df_year.groupby("Code", group_keys=False).apply(_fill_nearest)

    print(f"✔️ Ratings complétés. Shape : {df_filled.shape}\n")
    return df_filled[["Country", "Code", "Year", "rating_mean_num"]]

# =======================================================================================
# 4) DEFAULTS
# =======================================================================================

def load_defaults(base_dir: str) -> pd.DataFrame:
    print(" 3) LECTURE DES DÉFAUTS")

    path = os.path.join(base_dir, "Crédit_rating.xlsm")
    print(f"→ Fichier utilisé : {path}")

    df_def = pd.read_excel(path)

    if "Year" not in df_def.columns:
        df_def = df_def.rename(columns={"Unnamed: 0": "Year"})

    df_def["Year"] = pd.to_numeric(df_def["Year"], errors="coerce")
    df_def = df_def.dropna(subset=["Year"])
    df_def["Year"] = df_def["Year"].astype(int)

    code_cols = [c for c in df_def.columns if c not in ("Year", "Pays")]

    df_long = df_def.melt(
        id_vars=["Year"],
        value_vars=code_cols,
        var_name="Code",
        value_name="default_dummy"
    )
    df_long["default_dummy"] = df_long["default_dummy"].fillna(0).astype(int)

    print("✔️ Defaults → format long\n")
    return df_long

# =======================================================================================
# 5) BUILD MODEL DATASET — AVEC AR(1)
# =======================================================================================

def build_model_dataset(base_dir: str) -> pd.DataFrame:
    print("4) CONSTRUCTION DU DATASET FINAL")

    wb_panel = load_wb_panel(base_dir)
    ratings = load_ratings(base_dir, wb_panel)
    defaults = load_defaults(base_dir)

    # Merge WB + Ratings + Defaults
    df = wb_panel.merge(ratings, on=["Code", "Year"], how="left")
    df = df.merge(defaults, on=["Code", "Year"], how="left")
    df["default_dummy"] = df["default_dummy"].fillna(0).astype(int)

    # EM dummy
    EM = {
        "ARG","BRA","CHL","CHN","COL","ECU","EGY","HUN","IDN","IND",
        "MEX","MYS","PER","PHL","POL","ROU","THA","TUR","URY","VNM","ZAF"
    }
    df["is_em"] = df["Code"].isin(EM).astype(int)

    df = df.sort_values(["Code", "Year"])

    # Default lag cumulatif
    df["default_lag"] = df.groupby("Code")["default_dummy"].transform(lambda s: s.cummax())

    # ⭐⭐⭐ AR(1) : rating(t-1) = lag du rating continu
    df["rating_lag"] = df.groupby("Code")["rating_mean_num"].shift(1)

    # Interpolation macro
    macro_cols = [
        "GDP growth (annual %)",
        "GDP per capita (current US$)",
        "Inflation, consumer prices (annual %)",
        "Trade openness (% of GDP)",
        "Net lending/borrowing (% of GDP)",
        "Current account balance (% of GDP)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
    ]
    gouv_cols = ["Control of Corruption", "Political Stability and Absence of Violence"]

    df[macro_cols] = df.groupby("Code")[macro_cols].transform(
        lambda g: g.astype(float).interpolate().bfill().ffill()
    )
    df[gouv_cols] = df.groupby("Code")[gouv_cols].transform(
        lambda g: g.astype(float).bfill().ffill()
    )

    # Déficit
    df["Deficit (% of GDP)"] = -df["Net lending/borrowing (% of GDP)"]

    # Score ordinal
    df["score_mean_cat"] = df["rating_mean_num"].round().astype("Int64")

    # Colonnes du modèle (AR inclus)
    X_cols = [
        "GDP growth (annual %)",
        "GDP per capita (current US$)",
        "Debt (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "Control of Corruption",
        "Interest payments (% of GDP)",
        "is_em",
        "default_lag",
        "rating_lag",              # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AR(1)
    ]

    df_model = df.dropna(subset=X_cols + ["score_mean_cat"]).copy()

    out_path = os.path.join(base_dir, "model_dataset.xlsx")
    df_model.to_excel(out_path, index=False)
    print(f"✔️ Dataset final sauvegardé → {out_path}\n")

    return df_model, X_cols


# =======================================================================================
# 6) ESTIMATION DU MODÈLE ORDINAL (AVEC AR(1))
# =======================================================================================

def estimate_ordered_model(base_dir: str):
    # On récupère le dataset + la liste exacte des X
    df_model, X_cols = build_model_dataset(base_dir)

    # Variable dépendante = score ordinal
    y = df_model["score_mean_cat"].astype(int)
    X = df_model[X_cols]

    model = OrderedModel(y, X, distr="logit")
    result = model.fit(method="bfgs", disp=True)

    print(result.summary())
    return result, df_model, X_cols


# =======================================================================================
# 7) MAIN : ESTIMATION + TEST SUR LA DERNIÈRE ANNÉE
# =======================================================================================

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1) Estimation du modèle ordinal
    result, df_model, X_cols = estimate_ordered_model(base_dir)

    # 2) Distribution des scores observés
    print("\n===============================")
    print(" DISTRIBUTION DES SCORES OBSERVÉS")
    print("===============================\n")
    print(df_model["score_mean_cat"].value_counts().sort_index())

    # ===============================
    # 3) PRÉDICTION SUR LA DERNIÈRE ANNÉE DISPONIBLE
    # ===============================

    # Colonnes nécessaires pour faire le test
    cols_needed = X_cols + ["score_mean_cat", "rating_mean_num", "Year", "Code"]
    df_complete = df_model.dropna(subset=cols_needed).copy()

    if df_complete.empty:
        print("\n⚠️ Aucune observation complète pour le test sur la dernière année.")
    else:
        # Dernière année pour laquelle on a macro + ratings
        latest_year = int(df_complete["Year"].max())
        df_last = df_complete[df_complete["Year"] == latest_year].copy()

        if df_last.empty:
            print(f"\n⚠️ Aucune observation pour l'année {latest_year}.")
        else:
            print("\n===============================")
            print("   TEST SUR LA DERNIÈRE ANNÉE DISPONIBLE")
            print("===============================")
            print(f"Année testée : {latest_year}\n")

            # 3.1. Construire X pour cette année
            X_last = df_last[X_cols].astype(float)

            # 3.2. Prédire les probabilités par catégorie
            probs_last = result.model.predict(
                result.params,
                exog=X_last,
                which="prob"
            )
            probs_last = np.asarray(probs_last)  # (n_obs, n_categories)

            # 3.3. Récupérer les catégories possibles
            categories = np.sort(df_model["score_mean_cat"].dropna().unique())

            # 3.4. Catégorie la plus probable
            idx_max = probs_last.argmax(axis=1)
            predicted_cat = categories[idx_max]

            # 3.5. Score attendu = somme_k p_k * catégorie_k
            expected_score = (probs_last * categories).sum(axis=1)

            # 3.6. Ajout au DataFrame
            df_last["predicted_cat"] = predicted_cat.astype(int)
            df_last["expected_score"] = expected_score

            # Erreur vs rating moyen continu
            df_last["error_expected_vs_mean"] = (
                df_last["expected_score"] - df_last["rating_mean_num"]
            )

            # Erreur sur la catégorie (optionnel)
            df_last["error_cat_vs_score"] = (
                df_last["predicted_cat"] - df_last["score_mean_cat"]
            )

            # 3.7. Afficher le tableau des pays
            cols_show = [
                "Code",
                "Year",
                "rating_mean_num",
                "score_mean_cat",
                "expected_score",
                "predicted_cat",
                "error_expected_vs_mean",
            ]

            print(
                df_last[cols_show]
                .sort_values("Code")
            )

            # 3.8. MAE sur la dernière année
            mae = df_last["error_expected_vs_mean"].abs().mean()
            print(f"\nMAE (|expected_score - rating_mean_num|) sur {latest_year} : {mae:.3f}")

            # 3.9. Nombre de pays avec erreur < 1 notch
            n_below_1 = (df_last["error_expected_vs_mean"].abs() < 1).sum()
            print(f"Nombre de pays avec |erreur| < 1 : {n_below_1} / {len(df_last)}")

            # 3.10. Exemple : zoom sur l’Argentine (si présente)
            mask_arg = df_last["Code"] == "ARG"
            if mask_arg.any():
                print("\n--- Zoom ARG ---")
                print(df_last.loc[mask_arg, cols_show])


print(df_last[df_last["error_expected_vs_mean"].abs() > 0.5][[
    "Code", "rating_mean_num", "expected_score", "error_expected_vs_mean"
]].sort_values("error_expected_vs_mean"))
print(df_complete["score_mean_cat"].value_counts().sort_index())