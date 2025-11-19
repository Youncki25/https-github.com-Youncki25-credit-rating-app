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
    "Control of Corruption",
    "Political Stability and Absence of Violence",
]


def _standardize_wb_columns(df: pd.DataFrame, file_path: str | None = None) -> pd.DataFrame:
    """
    Corrige la colonne d'année et les fautes de frappe des colonnes WB,
    puis ne garde que Year + colonnes utiles.
    """
    fname = os.path.basename(file_path) if file_path else "WB_file"
    print(f"   Colonnes brutes WB ({fname}) : {list(df.columns)}")

    # 1) Détection de la colonne d'année
    year_col = None
    # a) Essayer Year / year / YEAR / date / Date / DATE
    for cand in ["Year", "year", "YEAR", "date", "Date", "DATE"]:
        if cand in df.columns:
            year_col = cand
            break

    # b) Sinon, chercher une colonne 'Unnamed' (par sécurité)
    if year_col is None:
        for c in df.columns:
            if "Unnamed" in str(c):
                year_col = c
                break

    if year_col is None:
        raise ValueError(
            f"Impossible de trouver la colonne année dans {fname}. "
            f"Colonnes disponibles : {list(df.columns)}"
        )

    # 2) Renommer en Year
    if year_col != "Year":
        print(f"   → Colonne année détectée '{year_col}', renommée en 'Year'")
        df = df.rename(columns={year_col: "Year"})

    # 3) Transformer Year en année (int)
    #    Si c'est une date, on prend .dt.year, sinon on essaie to_datetime.
    if np.issubdtype(df["Year"].dtype, np.number):
        # ex: déjà 1990, 1991...
        pass
    else:
        # essayer conversion en datetime, puis year
        year_conv = pd.to_datetime(df["Year"], errors="coerce")
        if year_conv.notna().any():
            df["Year"] = year_conv.dt.year
        else:
            # si vraiment impossible, on tente juste de caster en int
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        # on enlève les lignes où Year est NaN
        df = df[~df["Year"].isna()].copy()

    df["Year"] = df["Year"].astype(int)

    # 4) Corriger les fautes de frappe sur les noms d'indicateurs
    rename_map = {
        "Currrent account balance (% of GDP)": "Current account balance (% of GDP)",
        "Current account balancce (% of GDP)": "Current account balance (% of GDP)",
        "Control of Corruptioon": "Control of Corruption",
    }
    df = df.rename(columns=rename_map)

    # 5) Construire la liste des colonnes à garder : Year + indicateurs présents
    cols_to_keep = ["Year"]
    for col in WB_INDICATORS_CANON:
        if col in df.columns:
            cols_to_keep.append(col)

    print(f"   → Colonnes retenues après standardisation ({fname}) : {cols_to_keep}")
    df = df[cols_to_keep].copy()
    return df


def load_wb_panel(base_dir: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 1) LECTURE DES DONNÉES WB")
    print("===============================")

    pattern = os.path.join(base_dir, "*_WB_timeseries.xlsx")
    files = glob.glob(pattern)
    print(f"→ Fichiers WB détectés : {files}\n")

    all_list = []

    for path in files:
        code = os.path.basename(path).split("_")[0]  # ARG_WB_timeseries.xlsx → ARG
        print(f"→ Lecture fichier WB : {path}")
        try:
            df_raw = pd.read_excel(path, sheet_name=0)
            print("   ✔️ Lecture OK")

            df = _standardize_wb_columns(df_raw, file_path=path)
            df["Code"] = code
            df["Country"] = code  # nom simple = code pour l'instant

            all_list.append(df)
        except Exception as e:
            print(f"   ⚠️ Erreur lecture {path} : {e}")

        print()

    if not all_list:
        raise ValueError("Aucun fichier WB n'a pu être lu correctement (all_list vide).")

    wb_panel = pd.concat(all_list, ignore_index=True)
    print(f"✔️ WB Panel construit. Shape : {wb_panel.shape}")
    print(wb_panel.head(), "\n")

    return wb_panel


# ================================
# 2) LECTURE DES RATINGS
# ================================

def load_ratings(base_dir: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 2) LECTURE DES RATINGS MOYENS")
    print("===============================")

    path = os.path.join(base_dir, "Ratings.xlsx")
    print(f"→ Chemin Ratings : {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Ratings.xlsx introuvable à {path}")

    xls = pd.ExcelFile(path)
    print(f"→ Feuilles trouvées : {xls.sheet_names}")

    sheet = "Ratings" if "Ratings" in xls.sheet_names else "Sheet1"
    if sheet == "Sheet1":
        print("⚠️ Feuille 'Ratings' absente, utilisation de 'Sheet1'.")

    print(f"→ Lecture de la feuille '{sheet}'...")
    df = pd.read_excel(path, sheet_name=sheet)
    print("✔️ Lecture Ratings OK")
    print(f"✔️ Colonnes Ratings : {list(df.columns)}")

    cols_needed = ["Country", "Code", "Year", "rating_mean_num"]
    missing = [c for c in cols_needed if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans Ratings.xlsx : {missing}")

    df = df[cols_needed].copy()

    # moyenne au cas où plusieurs lignes par (pays, année)
    df_mean = (
        df.groupby(["Country", "Code", "Year"], as_index=False)["rating_mean_num"]
        .mean()
    )

    print("✔️ Aperçu Ratings moyens utilisés :")
    print(df_mean.head(10))

    return df_mean


# ================================
# 3) LECTURE DES DONNÉES DE DÉFAUT
# ================================

def load_defaults(path: str) -> pd.DataFrame:
    print("\n===============================")
    print(" 3) LECTURE DES DONNÉES DE DÉFAUT")
    print("===============================")

    print(f"→ Chemin défauts : {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier défauts introuvable : {path}")

    xls = pd.ExcelFile(path)
    print(f"→ Feuilles trouvées : {xls.sheet_names}")

    sheet = "Sheet1"
    print(f"→ Lecture de la feuille '{sheet}'...")
    df_def = pd.read_excel(path, sheet_name=sheet)
    print("✔️ Lecture defaults brute OK")
    print("   Colonnes lues :", list(df_def.columns))
    print(df_def.head())

    # colonne année
    if "Year" not in df_def.columns:
        print("→ La colonne Year n'existe pas, on renomme 'Unnamed: 0' en 'Year'")
        if "Unnamed: 0" not in df_def.columns:
            raise ValueError("Impossible de trouver la colonne année (Year ou Unnamed: 0).")
        df_def = df_def.rename(columns={"Unnamed: 0": "Year"})

    df_def["Year_num"] = pd.to_numeric(df_def["Year"], errors="coerce")
    print("→ Colonne Year_num après conversion :")
    print(df_def[["Year", "Year_num"]].head())

    df_def = df_def[~df_def["Year_num"].isna()].copy()
    df_def["Year"] = df_def["Year_num"].astype(int)
    df_def = df_def.drop(columns=["Year_num"])

    print(f"✔️ Lignes après nettoyage Year. Shape : {df_def.shape}")
    print(df_def.head())

    mapping_cols_to_code = {
        "France": "FRA",
        "US": "USA",
        "Argentine": "ARG",
        "Grèce": "GRC",
        "équateur": "ECU",
        "Egypte": "EGY",
        "Japon": "JPN",
        "Vietnam": "VNM",
        "Afrique du Sud": "ZAF",
        "Angleterre": "GBR",
    }

    print("→ Création des colonnes par code pays à partir des noms français...")
    keep_cols = ["Year"]
    for col in df_def.columns:
        if col in mapping_cols_to_code:
            code = mapping_cols_to_code[col]
            print(f"   {col}  →  {code}")
            df_def[code] = df_def[col]
            keep_cols.append(code)
        elif col not in ["Year", "Pays"]:
            print(f"   (ignorer la colonne '{col}', pas dans le mapping)")

    df_def = df_def[keep_cols].copy()
    print("✔️ Colonnes codes pays utilisées :", [c for c in df_def.columns if c != "Year"])
    print(df_def.head())

    df_long = df_def.melt(id_vars=["Year"], var_name="Code", value_name="default_dummy")
    df_long["default_dummy"] = df_long["default_dummy"].fillna(0).astype(int)
    df_long["Country"] = df_long["Code"]

    print(f"✔️ Defaults transformés en format long. Shape : {df_long.shape}")
    print(df_long.head())

    return df_long


# ================================
# 4) CONSTRUCTION DU DATASET FINAL
# ================================

def build_model_dataset(base_dir: str | None = None) -> pd.DataFrame:
    print("\n===============================")
    print(" 4) CONSTRUCTION DU DATASET FINAL")
    print("===============================")

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    print("→ Chargement WB...")
    wb_panel = load_wb_panel(base_dir)

    print("→ Chargement Ratings (mean_rating)...")
    ratings = load_ratings(base_dir)

    print("→ Chargement Defaults...")
    defaults_path = os.path.join(base_dir, "Crédit_rating.xlsm")
    defaults = load_defaults(defaults_path)

    print("\nColonnes WB :", list(wb_panel.columns))
    print("Colonnes Ratings :", list(ratings.columns))
    print("Colonnes Defaults :", list(defaults.columns))

    # Merge WB × Ratings sur Code, Year
    print("\n→ Merge WB × Ratings sur ['Code','Year']...")
    df = wb_panel.merge(
        ratings[["Country", "Code", "Year", "rating_mean_num"]],
        on=["Code", "Year"],
        how="left",
        suffixes=("", "_rat"),
    )
    print(f"✔️ Merge Ratings OK. Shape : {df.shape}")
    print(df.head(), "\n")

    # Merge avec Defaults
    print("→ Merge avec Defaults sur ['Code','Year']...")
    df = df.merge(
        defaults[["Year", "Code", "default_dummy"]],
        on=["Code", "Year"],
        how="left",
    )
    df["default_dummy"] = df["default_dummy"].fillna(0).astype(int)
    print(f"✔️ Merge Defaults OK. Shape : {df.shape}")
    print(df.head(), "\n")

    # Ajout indicatrice EM
    print("→ Ajout indicatrice EM...")
    em_countries = {"ARG", "ECU", "EGY", "VNM", "ZAF"}  # ajuste si besoin
    df["is_em"] = df["Code"].isin(em_countries).astype(int)

    # default_lag : défaut l'année précédente
    print("→ Calcul du default_lag...")
    df = df.sort_values(["Code", "Year"])
    df["default_lag"] = (
        df.groupby("Code")["default_dummy"].shift(1).fillna(0).astype(int)
    )

    print("\n✔️ Dataset final prêt. Shape :", df.shape)
    print(df.head(), "\n")

    # ============================
    # TRAITEMENT DES NA
    # ============================

    macro_cols = [
        "GDP growth (annual %)",
        "GDP per capita (current US$)",
        "Inflation, consumer prices (annual %)",
        "Trade openness (% of GDP)",
        "Net lending/borrowing (% of GDP)",
        "Current account balance (% of GDP)",
        "Debt (% of GDP)",
    ]

    gouv_cols = [
        "Control of Corruption",
        "Political Stability and Absence of Violence",
    ]

    print("=== Nombre de NA par colonne macro/gouv AVANT traitement ===")
    print(df[macro_cols + gouv_cols].isna().sum())

    # Interpolation macro par pays
    df[macro_cols] = df.groupby("Code")[macro_cols].transform(
        lambda g: g.interpolate(limit_direction="both")
    )

    # Gouvernance : ffill + bfill
    df[gouv_cols] = df.groupby("Code")[gouv_cols].transform(
        lambda g: g.ffill().bfill()
    )

    print("\n=== Nombre de NA par colonne macro/gouv APRÈS traitement ===")
    print(df[macro_cols + gouv_cols].isna().sum(), "\n")

    # ============================
    # Préparation dataset modèle
    # ============================

    df["score_mean_cat"] = df["rating_mean_num"].round().astype("Int64")

    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "is_em",
        "default_lag",
    ]

    print("→ Suppression des lignes sans rating ou sans X...")
    df_model = df.dropna(subset=X_cols + ["score_mean_cat"]).copy()
    print("✔️", df_model.shape, "lignes restantes\n")

    print("→ Variables explicatives utilisées :", X_cols)
    print("✔️ Dataset modèle prêt. Shape :", df_model.shape, "\n")

    return df_model


# ================================
# 5) ESTIMATION DU MODÈLE ORDINAL
# ================================

def estimate_ordered_model(base_dir: str | None = None):
    print("\n===============================")
    print(" 5) ESTIMATION DU MODÈLE ORDINAL")
    print("===============================")

    df_model = build_model_dataset(base_dir=base_dir)

    X_cols = [
        "GDP growth (annual %)",
        "Debt (% of GDP)",
        "Inflation, consumer prices (annual %)",
        "Current account balance (% of GDP)",
        "is_em",
        "default_lag",
    ]

    y = df_model["score_mean_cat"].astype(int)
    X = df_model[X_cols]

    print("→ Lancement Ordered Logit...")
    model = OrderedModel(y, X, distr="logit")
    result = model.fit(method="bfgs", disp=True)

    print("\n===============================")
    print("   RÉSULTATS DU MODÈLE ORDINAL")
    print("===============================")
    print(result.summary())

    return result, df_model


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    estimate_ordered_model(base_dir=base_dir)
