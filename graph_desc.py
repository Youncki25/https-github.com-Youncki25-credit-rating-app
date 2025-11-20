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

VARS = [
    "GDP growth (annual %)",
    "Debt (% of GDP)",
    "Inflation, consumer prices (annual %)",
    "Current account balance (% of GDP)",
]

GROUP_SIZE = 5


def load_all_countries():
    """Retourne un dict code_pays -> DataFrame."""
    files = glob.glob(WB_PATTERN)
    data = {}

    for path in files:
        code = os.path.basename(path).split("_")[0]
        df = pd.read_excel(path)

        if "date" in df.columns:
            df = df.rename(columns={"date": "Year"})

        if "Year" not in df.columns:
            print(f"⚠️ Pas de colonne 'Year' dans {path}, on saute.")
            continue

        df = df.sort_values("Year")
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

            # Titre global
            fig.suptitle(f"{var} – Groupe {g+1}", fontsize=14)

            for ax, code in zip(axes, group_countries):

                df = data[code]

                if var not in df.columns:
                    ax.set_title(f"{code} — (donnée manquante)")
                    ax.axis("off")
                    continue

                # Tracé
                ax.plot(df["Year"], df[var], marker="o", linewidth=1)

                # Titre du petit graphe
                ax.set_title(code)

                # SUPPRESSION DU LABEL Y
                ax.set_ylabel("")     # plus de texte
                ax.set_yticklabels([])  # plus de valeurs visuelles

                ax.grid(alpha=0.3)

            plt.tight_layout(rect=[0, 0, 1, 0.97])

            out_path = os.path.join(
                OUTPUT_DIR,
                f"group_{g+1}_{var.replace('%','pct').replace(' ','_')}.png"
            )
            plt.savefig(out_path, dpi=200)
            plt.close()

            print(f"✔️ Graph sauvegardé : {out_path}")


if __name__ == "__main__":
    plot_grouped_by_5()
    print("\n🎉 Tous les graphiques ont été générés dans :")
    print(OUTPUT_DIR)
