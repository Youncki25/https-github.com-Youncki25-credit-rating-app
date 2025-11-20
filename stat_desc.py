import pandas as pd
import glob
import os

# =========================
# CONFIG
# =========================
BASE_DIR = r"C:\Users\youne\https-github.com-Youncki25-credit-rating-app"
PATTERN = "*_WB_timeseries.xlsx"  # tous les fichiers pays
OUTFILE = "stats_descriptives_par_pays.xlsx"  # fichier final

# =========================
# SCRIPT
# =========================

def compute_stats_per_country():
    files = glob.glob(os.path.join(BASE_DIR, PATTERN))

    if not files:
        print("Aucun fichier *_WB_timeseries.xlsx trouvé.")
        return

    # Écriture Excel
    with pd.ExcelWriter(OUTFILE, engine="xlsxwriter") as writer:

        for path in files:
            country = os.path.basename(path).split("_")[0]  # ARG_WB_timeseries.xlsx → ARG

            print(f"→ Lecture : {path}")
            df = pd.read_excel(path)

            # Normalisation colonne année
            if "date" in df.columns:
                df = df.rename(columns={"date": "Year"})

            # Retirer Year des stats
            cols = [c for c in df.columns if c != "Year"]

            # Statistiques descriptives uniquement sur les colonnes utiles
            stats = df[cols].describe().T  # transpose = lisible

            # Écrire dans une feuille par pays
            stats.to_excel(writer, sheet_name=country)

            print(f"✔️ Statistiques écrites pour {country}")

    print(f"\n📁 FICHIER FINAL GÉNÉRÉ : {OUTFILE}")


if __name__ == "__main__":
    compute_stats_per_country()
