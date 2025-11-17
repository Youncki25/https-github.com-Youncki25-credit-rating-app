# API – US FRED (dette & ratios sur PIB)
# inutile- à check 
from fredapi import Fred
import pandas as pd
import matplotlib.pyplot as plt

fred = Fred(api_key='3c8e78b7fbab629ebde0669dc2f41f28')  # NE PAS MODIFIER

# --- Séries FRED (dette & budget) — CODES VALIDÉS ---
series_codes_debt_extended = {
    # A. Budget & PIB (trimestriel)
    "GDP": "GDP",
    "Federal_Surplus_Deficit": "FYFSD",
    "Gov_Expenditures": "FGEXPND",
    "Gov_Receipts": "FGRECPT",

    # B. Dette fédérale (niveaux + ratios %PIB)
    "Total_Public_Debt": "GFDEBTN",
    "Debt_Held_by_Public": "FYGFDPUN",
    "Debt_Held_by_Fed": "FDHBFRBN",
    "Debt_Held_by_Foreigners": "FDHBFIN",
    "Debt_Total_%GDP": "GFDEGDQ188S",
    "Debt_Public_%GDP": "FYGFGDQ188S",
    "Debt_Foreign_%GDP": "HBFIGDQ188S",

    # C. Intérêts
    "Net_Interest_Payments": "A091RC1Q027SBEA",
    "Interest_Outlays_%GDP": "FYOIGDA188S",  # annualisé (%PIB) — utile en contexte

    # D. Dette par secteur (Z.1, trimestriel)
    "Federal_Govt_Debt": "FGSDODNS",
    "State_Local_Debt": "SLGSDODNS",
    "Financial_Sector_Debt": "DODFS",
    "Household_Debt_Level": "CMDEBT",
    "Corp_Debt_Level": "BCNSDODNS",
    "Total_Credit_Market_Debt": "TCMDO",

    # E. Dette privée (%PIB) / crédit privé
    "Household_Debt_to_GDP": "HDTGPDUSQ163N",
    "Corp_Debt_to_GDP": "QUSPAM770A",
    "Private_Sector_Credit": "CRDQUSAPABIS",

    # F. Position extérieure / réserves (trimestriel)
    "Net_International_Investment_Position": "IIPUSNETIQ",
    "Foreign_Reserves": "IIPRESEQ",

    # G. Conditions de marché (quotidien)
    "10Y_Treasury_Yield": "GS10",
    "Yield_Curve_10Y2Y": "T10Y2Y",
    "Breakeven_Inflation_10Y": "T10YIE",
}

# --- Téléchargement intégral & préparation ---
data = pd.DataFrame({name: fred.get_series(code) for name, code in series_codes_debt_extended.items()})
data.index = pd.to_datetime(data.index)
data = data.sort_index().dropna(how='all')

# --- Ratios maison (% du PIB) à partir des niveaux trimestriels ---
if {'GDP','Federal_Surplus_Deficit','Total_Public_Debt','Debt_Held_by_Public','Net_Interest_Payments'}.issubset(data.columns):
    data['Deficit_to_GDP']         = data['Federal_Surplus_Deficit'] / data['GDP'] * 100
    data['Debt_to_GDP']            = data['Total_Public_Debt']       / data['GDP'] * 100
    data['Debt_PublicHeld_to_GDP'] = data['Debt_Held_by_Public']     / data['GDP'] * 100
    data['Interest_to_GDP']        = data['Net_Interest_Payments']   / data['GDP'] * 100

# --- Export complet ---
data.to_csv('fred_debt_history_full.csv', index_label='Date')
print("\n✅ Données complètes exportées dans 'fred_debt_history_full.csv'")

# --- Fenêtre d’analyse (depuis 2000) ---
START = '2000-01-01'
debut_periode = data.loc[data.index >= START].copy()

# --- Liste des plots (corrigée, uniquement séries existantes) ---
plots = [
    # Ratios calculés maison
    ('Deficit_to_GDP',         'Déficit budgétaire / PIB (%, trimestriel)',                'deficit_to_gdp.png',                '% du PIB'),
    ('Debt_to_GDP',            'Dette publique brute / PIB (%, trimestriel)',              'debt_to_gdp.png',                   '% du PIB'),
    ('Debt_PublicHeld_to_GDP', 'Dette détenue par le public / PIB (%, trimestriel)',       'debt_publicheld_to_gdp.png',        '% du PIB'),
    ('Interest_to_GDP',        'Intérêts nets payés / PIB (%, trimestriel)',               'interest_to_gdp.png',               '% du PIB'),

    # Budget/PIB (niveaux SAAR)
    ('GDP',                    'PIB nominal (SAAR, trimestriel)',                          'gdp.png',                           'Mds $ / SAAR'),
    ('Federal_Surplus_Deficit','Solde fédéral (SAAR, trimestriel)',                        'federal_deficit.png',               'Mds $ / SAAR'),
    ('Gov_Expenditures',       'Dépenses fédérales courantes (SAAR, trimestriel)',         'federal_expenditures.png',          'Mds $ / SAAR'),
    ('Gov_Receipts',           'Recettes fédérales courantes (SAAR, trimestriel)',         'federal_receipts.png',              'Mds $ / SAAR'),

    # Dette fédérale (niveaux & ratios FRED)
    ('Total_Public_Debt',      'Dette publique brute (niveau, fin de période)',            'total_public_debt.png',             'M $'),
    ('Debt_Held_by_Public',    'Dette détenue par le public (niveau)',                     'debt_held_by_public.png',           'M $'),
    ('Debt_Held_by_Fed',       'Dette détenue par la Fed (niveau)',                        'debt_held_by_fed.png',              'M $'),
    ('Debt_Held_by_Foreigners','Dette détenue par étrangers (niveau)',                     'debt_held_by_foreigners.png',       'Mds $'),
    ('Debt_Total_%GDP',        'Dette totale fédérale / PIB (%)',                          'debt_total_pct_gdp.png',            '% du PIB'),
    ('Debt_Public_%GDP',       'Dette détenue par le public / PIB (%)',                    'debt_public_pct_gdp.png',           '% du PIB'),
    ('Debt_Foreign_%GDP',      'Dette détenue par étrangers / PIB (%)',                    'debt_foreign_pct_gdp.png',          '% du PIB'),

    # Intérêts
    ('Net_Interest_Payments',  'Intérêts nets payés (BEA, SAAR, trimestriel)',             'net_interest_payments.png',         'Mds $ / SAAR'),
    ('Interest_Outlays_%GDP',  'Intérêts payés / PIB (%, annualisé OMB)',                  'interest_outlays_pct_gdp.png',      '% du PIB'),

    # Dette par secteur (Z.1)
    ('Federal_Govt_Debt',      'Dette gouvernement fédéral (Z.1, trimestriel)',            'z1_federal_debt.png',               'Mds $'),
    ('State_Local_Debt',       'Dette États & collectivités (Z.1, trimestriel)',           'z1_state_local_debt.png',           'Mds $'),
    ('Financial_Sector_Debt',  'Dette secteur financier (Z.1, trimestriel)',               'z1_financial_sector_debt.png',      'Mds $'),
    ('Household_Debt_Level',   'Dette des ménages (Z.1, trimestriel)',                     'z1_household_debt.png',             'Mds $'),
    ('Corp_Debt_Level',        'Dette entreprises non financières (Z.1, trimestriel)',     'z1_corp_debt.png',                  'Mds $'),
    ('Total_Credit_Market_Debt','Dette totale de marché (tous secteurs, trimestriel)',     'total_credit_market_debt.png',      'Mds $'),

    # Dette privée (%PIB) / crédit
    ('Household_Debt_to_GDP',  'Dette des ménages / PIB (%, trimestriel)',                 'household_debt_to_gdp.png',         '% du PIB'),
    ('Corp_Debt_to_GDP',       'Dette entreprises non financières / PIB (%, trimestriel)', 'corp_debt_to_gdp.png',              '% du PIB'),
    ('Private_Sector_Credit',  'Crédit domestique au secteur privé (niveau)',              'private_sector_credit.png',         'Mds $'),

    # Extérieur & réserves
    ('Net_International_Investment_Position','Position nette extérieure (trimestriel)',    'niip.png',                          'Mds $'),
    ('Foreign_Reserves',       'Réserves officielles (trimestriel)',                        'foreign_reserves.png',              'Mds $'),

    # Marché (quotidien)
    ('10Y_Treasury_Yield',     'Rendement 10 ans (%, quotidien)',                           'gs10.png',                          '%'),
    ('Yield_Curve_10Y2Y',      'Courbe 10Y-2Y (%, quotidien)',                               't10y2y.png',                        '%'),
    ('Breakeven_Inflation_10Y','Inflation implicite 10 ans (%, quotidien)',                 't10yie.png',                        '%'),
]

# --- Tracés (skip auto si colonne manquante) ---
for col, title, fname, ylabel in plots:
    if col not in debut_periode.columns:
        print(f"⏭️  Série absente: {col} — skip")
        continue
    s = debut_periode[col].dropna()
    if s.empty:
        print(f"⏭️  Série vide: {col} — skip")
        continue

    plt.figure(figsize=(10, 5))
    s.plot(linewidth=2)
    plt.title(title, fontsize=13, fontweight='bold')
    plt.ylabel(ylabel); plt.xlabel('')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(fname, dpi=150)
    plt.close()

print("✅ Graphiques enregistrés :", ", ".join([p[2] for p in plots if p[0] in debu