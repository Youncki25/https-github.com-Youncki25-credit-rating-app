import os
import glob
import numpy as np
import pandas as pd
from statsmodels.miscmodels.ordinal_model import OrderedModel

# ================================
# 0) CONFIG INDICATEURS WB
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


# ================================
# 1) OUTILS WB
# ================================

def _standardize_wb_columns(df: pd.DataFrame, file_path: str | None = None) -> pd.DataFrame:
    """
    Standardise les colonnes WB pour qu'elles aient :
      - une colonne 'Year' numérique
      - uniquement les colonnes de WB_INDICATORS_CANON
    """
    fname = os.path.basename(file_path) if file_path else "WB_file"
    print(f"   Colonnes brutes WB ({fname}) : {list(df.columns)}")

    # Détection de la colonne année
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

    # Conversion en année numérique
    if not np.issubdtype(df["Year"].dtype, np.number):
        year_conv = pd.to_datetime(df["Year"], errors="coerce")
        if year_conv.notna().any():
            df["Year"] = year_conv.dt.year
        else:
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    df = df[~df["Year"].isna()].copy()
    df["Year"] = df["Year"].astype(int)

    # Harmonisation des noms
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
    """
    Lit tous les fichiers {CODE}_WB_timeseries.xlsx dans base_dir
    et construit un panel WB avec :
      - Year
      - indicateurs macro
      - Code
      - Country (ici = Code)
    → PREND AUTOMATIQUEMENT TOUS LES PAYS
    """
    print("\n===============================")
    print(" 1) LECTURE DES DONNÉES WB")
    print("===============================")

    files = glob.glob(os.path.join(base_dir, "*_WB_timeseries.xlsx"))
    print(f"→ Fichiers WB détectés : {files}\n")

    if not files:
        raise FileNotFoundError("Aucun fichier *_WB_timeseries.xlsx trouvé dans base_dir.")

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
# 2) LECTURE DES RATINGS (Rating_API.xlsx)
# ================================

def load_ratings(base_dir: str, wb_panel: pd.DataFrame) -> pd.DataFrame:
    """
    Charge Rating_API.xlsx (chemin absolu donné), construit :
      - une note moyenne numérique par (Country, Code, Year)
      - complétée par la donnée la plus proche si une année manque (nearest)
    """
    print("\n===============================")
    print(" 2) LECTURE DES RATINGS")
    print("===============================")

    # Chemin absolu fourni
    path = "/Users/beldjenna/Desktop/Rating Algo/Rating_API.xlsx"
    print(f"→ Fichier de ratings utilisé : {path}")

    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    print(f"   Colonnes brutes Ratings : {list(df.columns)}")

    # On part toujours d’une annualisation propre :
    # moyenne par (Country, Code, Year) de rating_mean_num
    if "rating_mean_num" not in df.columns or "Year" not in df.columns:
        raise ValueError("Rating_API.xlsx doit contenir au moins 'Year' et 'rating_mean_num'.")

    df_year = (
        df.groupby(["Country", "Code", "Year"], as_index=False)["rating_mean_num"]
          .mean()
    )

    # S'assurer qu'on a les colonnes clés
    needed = ["Country", "Code", "Year", "rating_mean_num"]
    missing = [c for c in needed if c not in df_year.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans ratings annualisés : {missing}")

    # Restreindre aux pays présents dans WB (notre univers de modèle)
    wb_codes = wb_panel["Code"].unique()
    df_year = df_year[df_year["Code"].isin(wb_codes)].copy()

    print(f"✔️ Ratings annuels chargés. Shape : {df_year.shape}")

    # Compléter les années manquantes par pays en prenant la valeur la plus proche
    print("→ Complétion des années manquantes (rating_mean_num) par pays (nearest)...")

    def _fill_nearest(group: pd.DataFrame) -> pd.DataFrame:
        # On trie par année et on s'assure d'un seul enregistrement par Year
        group = group.sort_values("Year")
        group = (
            group.groupby("Year", as_index=True)
                 .agg({
                     "rating_mean_num": "mean",
                     "Code": "first",
                     "Country": "first",
                 })
        )

        code = group["Code"].iloc[0]

        # Grille d'années basée sur WB pour ce pays
        years_wb = wb_panel[wb_panel["Code"] == code]["Year"]
        if years_wb.empty:
            return group.reset_index()

        year_min = int(years_wb.min())
        year_max = int(years_wb.max())
        full_years = range(year_min, year_max + 1)

        # Reindex sur toutes les années WB (index = Year, unique donc OK)
        group = group.reindex(full_years)

        # Re-remplir Code / Country
        group["Code"] = code
        country_val = group["Country"].dropna().iloc[0] if group["Country"].notna().any() else code
        group["Country"] = country_val

        # Interpolation nearest sur rating_mean_num
        group["rating_mean_num"] = (
            group["rating_mean_num"]
            .astype(float)
            .interpolate(method="nearest", limit_direction="both")
        )

        group["Year"] = group.index
        return group.reset_index(drop=True)

    df_filled = (
        df_year.groupby("Code", group_keys=False)
               .apply(_fill_nearest)
    )

    print(f"✔️ Ratings complétés (nearest). Shape : {df_filled.shape}\n")
    return df_filled[["Country", "Code", "Year", "rating_mean_num"]]


# ================================
# 3) LECTURE DES DONNÉES DE DÉFAUT
# ================================

def load_defaults() -> pd.DataFrame:
    """
    Charge les défauts depuis le fichier Crédit_rating.xlsm.
    Le fichier contient :
       - Year
       - colonnes de pays déjà en codes ISO3 (ARG, FRA, GRC, VEN, etc.)
    On convertit en format long : Year, Code, default_dummy.
    """
    print("\n===============================")
    print(" 3) LECTURE DES DÉFAUTS")
    print("===============================")

    path = "/Users/beldjenna/Desktop/Rating Algo/Crédit_rating.xlsm"
    print(f"→ Fichier de défauts utilisé : {path}")

    df_def = pd.read_excel(path)

    # Harmonisation colonne Year
    if "Year" not in df_def.columns:
        df_def = df_def.rename(columns={"Unnamed: 0": "Year"})

    df_def["Year"] = pd.to_numeric(df_def["Year"], errors="coerce")
    df_def = df_def.dropna(subset=["Year"])
    df_def["Year"] = df_def["Year"].astype(int)

    # Toutes les colonnes sauf Year & Pays sont déjà des codes ISO3
    code_cols = [c for c in df_def.columns if c not in ("Year", "Pays")]

    # Format long
    df_long = df_def.melt(
        id_vars=["Year"],
        value_vars=code_cols,
        var_name="Code",
        value_name="default_dummy"
    )

    df_long["default_dummy"] = df_long["default_dummy"].fillna(0).astype(int)

    print("✔️ Defaults chargés → format long (Year, Code, default_dummy)\n")
    return df_long



# ================================
# 4) CONSTRUCTION DU DATASET
# ================================

def build_model_dataset(base_dir: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 4) CONSTRUCTION DU DATASET FINAL")
    print("===============================")

    wb_panel = load_wb_panel(base_dir)
    ratings = load_ratings(base_dir, wb_panel)
    defaults = load_defaults()

    # Merge WB + Ratings
    df = wb_panel.merge(ratings, on=["Code", "Year"], how="left")

    # Merge Defaults
    df = df.merge(defaults, on=["Code", "Year"], how="left")
    df["default_dummy"] = df["default_dummy"].fillna(0).astype(int)

    # EM dummy (liste à ajuster si tu veux)
    EM = {"ARG", "ECU", "EGY", "VNM", "ZAF"}
    df["is_em"] = df["Code"].isin(EM).astype(int)

    # Lag défaut
    df = df.sort_values(["Code", "Year"])
    df["default_lag"] = df.groupby("Code")["default_dummy"].shift(1).fillna(0).astype(int)

    # Imputation NA sur macro et gouvernance
    macro_cols = [
        "GDP growth (annual %)", "GDP per capita (current US$)",
        "Inflation, consumer prices (annual %)", "Trade openness (% of GDP)",
        "Net lending/borrowing (% of GDP)", "Current account balance (% of GDP)",
        "Debt (% of GDP)", "Interest payments (% of GDP)"
    ]
    gouv_cols = ["Control of Corruption", "Political Stability and Absence of Violence"]

    df[macro_cols] = df.groupby("Code")[macro_cols].transform(
        lambda g: g.astype(float).interpolate().bfill().ffill()
    )
    df[gouv_cols] = df.groupby("Code")[gouv_cols].transform(
        lambda g: g.astype(float).bfill().ffill()
    )

    # Déficit = - net lending/borrowing (% PIB)
    df["Deficit (% of GDP)"] = -df["Net lending/borrowing (% of GDP)"]

    # Variable de score ordinal (catégorie la plus proche)
    df["score_mean_cat"] = df["rating_mean_num"].round().astype("Int64")

    # Variables explicatives retenues
    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "is_em",
        "default_lag",
    ]

    # On ne garde que les lignes où tout est dispo
    df_model = df.dropna(subset=X_cols + ["score_mean_cat"]).copy()

    # Sauvegarde pour inspection
    out_path = os.path.join(base_dir, "model_dataset.xlsx")
    df_model.to_excel(out_path, index=False)
    print(f"✔️ Dataset final sauvegardé → {out_path}\n")

    return df_model


# ================================
# 5) ESTIMATION DU MODÈLE
# ================================

def estimate_ordered_model(base_dir: str):
    df_model = build_model_dataset(base_dir)

    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Interest payments (% of GDP)",
        "Deficit (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "is_em",
        "default_lag",
    ]

    y = df_model["score_mean_cat"].astype(int)
    X = df_model[X_cols]

    model = OrderedModel(y, X, distr="logit")
    result = model.fit(method="bfgs", disp=True)

    print(result.summary())
    return result, df_model, X_cols


# ================================
# 6) MAIN + EXEMPLE DE PRÉDICTION
# ================================

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    result, df_model, X_cols = estimate_ordered_model(base_dir)

    # Exemple de vecteur de caractéristiques (à adapter)
    X_new = {
        "GDP growth (annual %)": -0.23,
        "Debt (% of GDP)": 63.5,
        "Interest payments (% of GDP)": 1.5,
        "Deficit (% of GDP)": 2.5,
        "Inflation, consumer prices (annual %)": 2.25,
        "Current account balance (% of GDP)": 5.66,
        "is_em": 0,         # 0 = DM, 1 = EM
        "default_lag": 0,   # 1 si défaut l'année précédente
    }

    X_new_df = pd.DataFrame([X_new])[X_cols]

    # Probabilités par catégorie
    probs = result.model.predict(result.params, exog=X_new_df, which="prob")

    # Récupérer les catégories observées
    categories = np.sort(df_model["score_mean_cat"].dropna().unique())

    idx_max = int(np.argmax(probs[0]))
    predicted_cat = int(categories[idx_max])

    expected_score = float((probs[0] * categories).sum())

    print("\n===============================")
    print("   PRÉDICTION AVEC LE MODÈLE ORDINAL")
    print("===============================")
    print("Probabilités par catégorie (dans l'ordre des catégories) :")
    for c, p in zip(categories, probs[0]):
        print(f"  P(score = {int(c)}) = {p:.4f}")
    print(f"\nCatégorie la plus probable      : {predicted_cat}")
    print(f"Score attendu (valeur moyenne)  : {expected_score:.2f}")

      # ================================
    # 7) TEST : PREDIRE POUR UN PAYS ALÉATOIRE EN 2024
    # ================================
    print("\n====================================")
    print(" TEST SUR UN PAYS ALÉATOIRE (année 2024)")
    print("====================================")

    # 1. On filtre les observations de 2024
    df_2024 = df_model[df_model["Year"] == 2024].copy()

    if df_2024.empty:
        print("⚠️ Aucun pays dans df_model pour l’année 2024 !")
    else:
        # 2. Choisir un pays aléatoire (on garde un DataFrame, pas une Series)
        random_row = df_2024.sample(1)  # DataFrame 1 ligne
        code_test = random_row["Code"].iloc[0]
        true_score = int(random_row["score_mean_cat"].iloc[0])

        print(f"Pays sélectionné : {code_test}")
        print(f"Note réelle 2024 : {true_score}")

        # 3. Construire le vecteur X_test à partir des données réelles
        #    et s'assurer qu'il est bien numérique
        X_test = random_row[X_cols].astype(float)

        # 4. Prédire les probas
        probs_test = result.model.predict(result.params, exog=X_test, which="prob")

        # 5. Trouver la catégorie prédite
        categories_sorted = np.sort(df_model["score_mean_cat"].dropna().unique())
        idx_pred = int(np.argmax(probs_test[0]))
        predicted_score = int(categories_sorted[idx_pred])

        print("\nProbabilités par catégorie :")
        for c, p in zip(categories_sorted, probs_test[0]):
            print(f"  P(score = {int(c)}) = {p:.4f}")

        expected_score = float((probs_test[0] * categories_sorted).sum())

        print("\n🎯 Résultat test :")
        print(f"  - Pays            : {code_test}")
        print(f"  - Note réelle     : {true_score}")
        print(f"  - Note prédite    : {predicted_score}")
        print(f"  - Score attendu   : {expected_score:.2f}")
