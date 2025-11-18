# -*- coding: utf-8 -*-

import os
import glob
import numpy as np
import pandas as pd
from statsmodels.miscmodels.ordinal_model import OrderedModel





# ================================
# 0) PARAMÈTRES
# ================================

COUNTRIES = ["FRA","GRC","JPN","USA","ECU","VNM","ZAF","ARG","EGY","GBR"]

YEAR_START = 1990
YEAR_END = 2024

EM_COUNTRIES = ["ECU","VNM","ZAF","ARG","EGY"]


WB_INDICATORS = [
    "GDP growth (annual %)",
    "GDP per capita (current US$)",
    "Inflation, consumer prices (annual %)",
    "Trade openness (% of GDP)",
    "Debt (% of GDP)",
    "Net lending/borrowing (% of GDP)",
    "Current account balance (% of GDP)",
    "Control of Corruption",
    "Political Stability and Absence of Violence"
]


# ================================
# 1) LOAD WB DATA
# ================================

def load_wb_panel(base_dir):

    print("\n===============================")
    print(" 1) LECTURE DES DONNÉES WB")
    print("===============================")

    pattern = os.path.join(base_dir, "*_WB_timeseries.xlsx")
    files = glob.glob(pattern)

    print(f"→ Fichiers WB détectés : {files}")

    if len(files) == 0:
        raise FileNotFoundError("Aucun fichier *_WB_timeseries.xlsx trouvé.")

    all_list = []

    for path in files:
        print(f"\n→ Lecture fichier WB : {path}")

        fname = os.path.basename(path)
        code = fname.split("_")[0]

        if code not in COUNTRIES:
            print(f"   ❌ {code} ignoré (pas dans COUNTRIES)")
            continue

        df_raw = pd.read_excel(path)
        print("   ✔️ Lecture OK")

        if "date" not in df_raw.columns:
            raise ValueError(f"❌ Le fichier {fname} ne contient pas 'date'")

        df_raw = df_raw.rename(columns={"date": "Year"})
        df_raw["Year"] = df_raw["Year"].astype(int)

        df_raw = df_raw[(df_raw["Year"] >= YEAR_START) & (df_raw["Year"] <= YEAR_END)]

        ind_cols = [c for c in WB_INDICATORS if c in df_raw.columns]

        df_country = df_raw[["Year"] + ind_cols].copy()
        df_country["Code"] = code
        df_country["Country"] = code

        print(f"   ✔️ Colonnes retenues : {ind_cols}")

        all_list.append(df_country)

    wb_panel = pd.concat(all_list, ignore_index=True)
    print("\n✔️ WB Panel construit. Shape :", wb_panel.shape)
    print(wb_panel.head())

    return wb_panel


#ratings

def load_ratings(path):

    print("\n===============================")
    print(" 2) LECTURE DES RATINGS MOYENS")
    print("===============================")

    print(f"→ Chemin Ratings : {path}")

    if not os.path.exists(path):
        raise FileNotFoundError("❌ Ratings.xlsx introuvable.")

    xls = pd.ExcelFile(path)
    print("→ Feuilles trouvées :", xls.sheet_names)

    # --- Choix intelligent de la feuille ---
    if "Ratings" in xls.sheet_names:
        sheet_name = "Ratings"
    elif "Sheet1" in xls.sheet_names:
        sheet_name = "Sheet1"
        print("⚠️ Feuille 'Ratings' absente, utilisation de 'Sheet1'.")
    else:
        # on prend la première feuille par défaut
        sheet_name = xls.sheet_names[0]
        print(f"⚠️ Ni 'Ratings' ni 'Sheet1' trouvées, utilisation de '{sheet_name}'.")

    print(f"→ Lecture de la feuille '{sheet_name}'...")
    df_rat = pd.read_excel(path, sheet_name=sheet_name)
    print("✔️ Lecture Ratings OK")
    print("✔️ Colonnes Ratings :", df_rat.columns.tolist())
    print(df_rat.head())

    # On s'assure qu'on a bien Country, Code, Year
    base_required = {"Country", "Code", "Year"}
    missing_base = base_required - set(df_rat.columns)
    if missing_base:
        raise ValueError(f"❌ Colonnes manquantes dans Ratings.xlsx : {missing_base}")

    # Gestion de la colonne de moyenne :
    # - soit tu as 'rating_mean_num'
    # - soit tu as 'mean_rating' (ton nouveau fichier)
    if "rating_mean_num" not in df_rat.columns:
        if "mean_rating" in df_rat.columns:
            df_rat = df_rat.rename(columns={"mean_rating": "rating_mean_num"})
            print("→ Colonne 'mean_rating' renommée en 'rating_mean_num'")
        else:
            raise ValueError(
                "❌ Ni 'rating_mean_num' ni 'mean_rating' trouvées dans Ratings.xlsx"
            )

    # Conversion Year en int
    df_rat["Year"] = pd.to_numeric(df_rat["Year"], errors="coerce")
    df_rat = df_rat.dropna(subset=["Year"]).copy()
    df_rat["Year"] = df_rat["Year"].astype(int)

    # Conversion rating_mean_num en numérique
    df_rat["rating_mean_num"] = pd.to_numeric(df_rat["rating_mean_num"], errors="coerce")

    print("✔️ Aperçu Ratings moyens utilisés :")
    print(df_rat[["Country", "Code", "Year", "rating_mean_num"]].head(10))

    return df_rat[["Country", "Code", "Year", "rating_mean_num"]]

# ================================
# 3) LOAD DEFAULTS (wide → long)
# ================================

def load_defaults(path):

    print("\n===============================")
    print(" 3) LECTURE DES DONNÉES DE DÉFAUT")
    print("===============================")

    print(f"→ Chemin défauts : {path}")

    if not os.path.exists(path):
        raise FileNotFoundError("❌ Crédit_rating.xlsm introuvable")

    xls = pd.ExcelFile(path)
    print("→ Feuilles trouvées :", xls.sheet_names)

    sheet_name = "Sheet1"
    if sheet_name not in xls.sheet_names:
        raise ValueError(f"❌ Feuille {sheet_name} introuvable dans Crédit_rating.xlsm")

    print(f"→ Lecture de la feuille '{sheet_name}'...")
    df_def = pd.read_excel(path, sheet_name=sheet_name)
    print("✔️ Lecture defaults brute OK")
    print("   Colonnes lues :", df_def.columns.tolist())
    print(df_def.head())

    # 1) Colonne Year
    if "Year" not in df_def.columns:
        first_col = df_def.columns[0]
        print(f"→ La colonne Year n'existe pas, on renomme '{first_col}' en 'Year'")
        df_def = df_def.rename(columns={first_col: "Year"})

    # 2) Nettoyage Year : enlever 'Date'
    df_def["Year_num"] = pd.to_numeric(df_def["Year"], errors="coerce")
    print("→ Colonne Year_num après conversion :")
    print(df_def[["Year", "Year_num"]].head())

    df_def = df_def[~df_def["Year_num"].isna()].copy()
    df_def["Year"] = df_def["Year_num"].astype(int)
    df_def = df_def.drop(columns=["Year_num"])

    print("✔️ Lignes après nettoyage Year. Shape :", df_def.shape)
    print(df_def.head())

    # 3) Mapping FR → codes ISO
    country_map = {
        "France": "FRA",
        "Grèce": "GRC",
        "Japon": "JPN",
        "US": "USA",
        "équateur": "ECU",
        "Equateur": "ECU",
        "Vietnam": "VNM",
        "Afrique du Sud": "ZAF",
        "Argentine": "ARG",
        "Egypte": "EGY",
        "Angleterre": "GBR",
    }

    df_work = df_def[["Year"]].copy()
    mapped_cols = []

    print("→ Création des colonnes par code pays à partir des noms français...")

    for col in df_def.columns:
        if col in ["Year", "Pays"]:
            continue
        if col in country_map:
            code = country_map[col]
            df_work[code] = df_def[col]
            mapped_cols.append(code)
            print(f"   {col}  →  {code}")
        else:
            print(f"   (ignorer la colonne '{col}', pas dans le mapping)")

    if not mapped_cols:
        raise ValueError("❌ Aucune colonne pays n'a été mappée. Vérifie le mapping country_map.")

    print("✔️ Colonnes codes pays utilisées :", mapped_cols)
    print(df_work.head())

    # 4) wide → long
    df_long = df_work.melt(
        id_vars="Year",
        value_vars=mapped_cols,
        var_name="Code",
        value_name="default_dummy"
    )

    df_long["default_dummy"] = df_long["default_dummy"].fillna(0).astype(int)
    df_long["Country"] = df_long["Code"]

    print("✔️ Defaults transformés en format long. Shape :", df_long.shape)
    print(df_long.head())

    return df_long


# ================================
# 4) BUILD DATASET FINAL
# ================================

def build_model_dataset():

    print("\n===============================")
    print(" 4) CONSTRUCTION DU DATASET FINAL")
    print("===============================")

    base_dir = r"C:\Users\youne\https-github.com-Youncki25-credit-rating-app"
    # Sur Mac tu mettras : base_dir = "/Users/beldjenna/Desktop/Rating Algo"

    print("\n→ Chargement WB...")
    wb = load_wb_panel(base_dir)

    print("\n→ Chargement Ratings (mean_rating)...")
    df_rat = load_ratings(os.path.join(base_dir, "Ratings.xlsx"))

    print("\n→ Chargement Defaults...")
    df_def = load_defaults(os.path.join(base_dir, "Crédit_rating.xlsm"))

    print("\nColonnes WB :", wb.columns.tolist())
    print("Colonnes Ratings :", df_rat.columns.tolist())
    print("Colonnes Defaults :", df_def.columns.tolist())

    # ==========================
    # 1) Merge WB × Ratings
    # ==========================

    print("\n→ Merge WB × Ratings sur ['Code','Year']...")
    df = wb.merge(
        df_rat[["Code", "Year", "rating_mean_num"]],   # on garde que ce qui sert
        on=["Code", "Year"],
        how="left"
    )
    print("✔️ Merge Ratings OK. Shape :", df.shape)
    print(df.head())

    # ==========================
    # 2) Merge avec Defaults
    # ==========================

    print("\n→ Merge avec Defaults sur ['Code','Year']...")
    df = df.merge(
        df_def[["Code", "Year", "default_dummy"]],
        on=["Code", "Year"],
        how="left"
    )
    df["default_dummy"] = df["default_dummy"].fillna(0).astype(int)
    print("✔️ Merge Defaults OK. Shape :", df.shape)
    print(df.head())

    # ==========================
    # 3) Ajout indicatrice EM + default_lag
    # ==========================

    print("\n→ Ajout indicatrice EM...")
    df["is_em"] = df["Code"].isin(EM_COUNTRIES).astype(int)

    print("→ Calcul du default_lag...")
    df = df.sort_values(["Code", "Year"])
    df["default_lag"] = df.groupby("Code")["default_dummy"].shift(1).fillna(0).astype(int)

    print("\n✔️ Dataset final prêt. Shape :", df.shape)
    print(df.head())

    return df


# ================================
# 5) MODEL ESTIMATION
# ================================

def estimate_ordered_model():

    print("\n===============================")
    print(" 5) ESTIMATION DU MODÈLE ORDINAL")
    print("===============================")

    df = build_model_dataset()

    print("\n→ Suppression des lignes sans rating...")
    df = df.dropna(subset=["rating_mean_num"])
    print("✔️", df.shape, "lignes restantes")

    df["score_mean_cat"] = df["rating_mean_num"].round().astype(int)

    X_cols = [
        "GDP growth (annual %)",
        "GDP per capita (current US$)",
        "Inflation, consumer prices (annual %)",
        "Trade openness (% of GDP)",
        "Debt (% of GDP)",
        "Net lending/borrowing (% of GDP)",
        "Current account balance (% of GDP)",
        "Control of Corruption",
        "Political Stability and Absence of Violence",
        "is_em",
        "default_lag"
    ]

    X_cols = [c for c in X_cols if c in df.columns]

    print("\n→ Variables explicatives utilisées :", X_cols)

    df_model = df.dropna(subset=X_cols).copy()
    print("✔️ Dataset modèle prêt. Shape :", df_model.shape)

    y = pd.Categorical(df_model["score_mean_cat"], ordered=True)
    X = df_model[X_cols]

    print("\n→ Lancement Ordered Logit...")
    model = OrderedModel(y, X, distr="logit")
    result = model.fit(method="bfgs")

    print("\n===============================")
    print("   RÉSULTATS DU MODÈLE ORDINAL")
    print("===============================")
    print(result.summary())
    print("===============================")

    return result, df_model


# ================================
# 6) MAIN
# ================================

if __name__ == "__main__":
    result, df_model = estimate_ordered_model()
    