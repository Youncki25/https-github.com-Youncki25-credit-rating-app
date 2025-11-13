import QuantLib as ql
import pandas as pd

def make_schedule(
    start, end, freq, calendar, convention,
    eom=False, rule=ql.DateGeneration.Forward,
    first=None, next_to_last=None
):
    return ql.Schedule(
        start, end, ql.Period(freq), calendar,
        convention, convention, rule, eom,
        first if first else ql.Date(),
        next_to_last if next_to_last else ql.Date()
    )

# --------------------------
# Paramètres du schedule
# --------------------------
start_d = ql.Date(1, 1, 2025)
end_d = ql.Date(1, 1, 2035)
freq = ql.Quaterly            # 6 mois
calendar = ql.TARGET()
convention = ql.ModifiedFollowing
rule = ql.DateGeneration.Forward
eom = False


schedule = make_schedule(start_d, end_d, freq, calendar, convention, eom, rule)


start_dates = list(schedule)[:-1]
end_dates = list(schedule)[1:]




# iso pour la conversion en string lisible (pas quantlib)
df = pd.DataFrame({
    "Date Début": [d.ISO() for d in start_dates],
    "Date Fin": [d.ISO() for d in end_dates],
    "Convention": [str(convention)] * len(start_dates),
    "Calendrier": [calendar.name()] * len(start_dates),
    "Règle": ["Forward" if rule == ql.DateGeneration.Forward else "Backward"] * len(start_dates)
})

print(df)
