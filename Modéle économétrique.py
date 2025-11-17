# Modéle économétrique
#MG : Ratings
# Inès : Défaut , VBA for each ---> mettre 0 si pas de défaut et 1 si défaut
# Conitnue  Modélé éconoémtrique
#yt=B0+B1PIB+B2INF+B3FISCAL_BALANCE+B4UNEMPLOYMENT+B5INTEREST_PAYMENTS+B6TAX_REVENUE +B7DUMMY_DEFAULT_PREVIOUS+B8DUMMY_DEVELOPED_COUNTRY +B9RATINGS +e
import pandas as pd
import numpy as np
from statsmodels.miscmodels.ordinal_model import OrderedModel

# On a 3 type d'excel à pas oublier les data macro, les ratings moyen et l'indicat de défaut

