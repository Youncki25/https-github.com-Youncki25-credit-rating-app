import os
import glob
import math
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================

BASE_DIR = r"C:\Users\youne\https-github.com-Youncki25-credit-rating-app"
WB_PATTERN = os.path.join(BASE_DIR, "*_WB_timeseries.xlsx")

OUTPUT_DIR = r"C:\Users\youne\https-github.com-Youncki25-credit-rating-app\Photo\graphique"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Nouvelles variables demandées
VARS = [
    "Net lending/borrowing (% of GDP)",
    "Interest payments (% of GDP)",
    "Trade Balance (% of GDP) [constructed]",
]

GROUP_SIZE = 5


def load_all_countries():
    files = glob.glob(WB_PATTERN)
    data = {}

    for path in files:
        code = os.path.basename(path).split("_")[0]
        df = pd.read_excel(path)

        if "date" in df.columns:
            df = df.rename(columns={"date": "Year"})

        if "Year" not in df.columns:
            print(f"⚠️ Pas de colonne Year dans {path}, ignoré.")
            continue

        df = df.sort_values("Year")

        # ⚠️ Refaire la balance commerciale si absente
        if "Trade Balance (% of GDP) [constructed]" not in df.columns:
            if "Exports of goods and services (% of GDP)" in df.columns and \
               "Imports of goods and services (% of GDP)" in df.columns:
                df["Trade Balance (% of GDP) [constructed]"] = (
                    df["Exports of goods and services (% of GDP)"]
                    - df["Imports of goods and services (% of GDP)"]
                )

        data[code] = df

    return data


def plot_grouped_by_5():
    data = load_all_countries()
    country_list = sorted(data.keys())
    n_groups = math.ceil(len(country_list) / GROUP_SIZE)

    for var in VARS:
        for g in range(n_groups):

            group_countries = country_list[g*GROUP_SIZE : (g+1)*GROUP_SIZE]
            if not group_countries:
                continue

            fig, axes = plt.subplots(len(group_countries), 1, figsize=(8, 10))
            if len(group_countries) == 1:
                axes = [axes]

            fig.suptitle(f"{var} – Groupe {g+1}", fontsize=15)

            for ax, code in zip(axes, group_countries):

                df = data[code]

                if var not in df.columns:
                    ax.text(0.5, 0.5, f"{code} : donnée manquante",
                            ha="center", va="center")
                    ax.axis("off")
                    continue

                ax.plot(df["Year"], df[var], marker="o", linewidth=1.3)
                ax.set_title(code, fontsize=12)
                ax.grid(alpha=0.3)

                ax.set_xlabel("")                 # enlève label X
                ax.set_ylabel("")                 # enlève label Y

            plt.tight_layout(rect=[0, 0, 1, 0.96])

            clean_name = var.replace("%", "pct").replace(" ", "_").replace("/", "")
            out_path = os.path.join(OUTPUT_DIR, f"group_{g+1}_{clean_name}.png")

            plt.savefig(out_path, dpi=200)
            plt.close()

            print(f"✔️ Graph sauvegardé : {out_path}")


if __name__ == "__main__":
    plot_grouped_by_5()
    print("\n🎉 Graphiques déficit, intérêts et balance commerciale générés !")
    print("📁 Dossier :", OUTPUT_DIR)
