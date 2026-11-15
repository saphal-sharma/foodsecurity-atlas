"""
Load source data into a SQLite database (data/atlas.db) and compute per-country statistics.

Tables created
  countries        ISO3 code, name, UN region and sub-region
  cereal_yield     country-year cereal yield (t/ha) and nitrogen use (kg/ha), FAO via OWID
  population       country-year population, World Bank via datahub
  cereal_stats     per-country yield level, trend and volatility (computed here)
  wb_indicators    optional: World Bank indicators downloaded by src/fetch_worldbank.py
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
DB = D / "atlas.db"


def yield_stats(g: pd.DataFrame) -> pd.Series:
    w = g[g["year"].between(1999, 2018)].dropna(subset=["cereal_t_ha"])
    if len(w) < 15:
        return pd.Series(dtype=float)
    yrs, y = w["year"].to_numpy(), w["cereal_t_ha"].to_numpy()
    slope_log = np.polyfit(yrs, np.log(y), 1)[0]
    fit = np.polyval(np.polyfit(yrs, y, 1), yrs)
    recent = g[g["year"].between(2014, 2018)]
    return pd.Series({
        "yield_2014_18_t_ha": recent["cereal_t_ha"].mean(),
        "yield_trend_pct_yr": (np.exp(slope_log) - 1) * 100,
        "yield_volatility_cv_pct": np.std(y - fit) / np.mean(fit) * 100,
        "n_use_2013_17_kg_ha": recent["n_kg_ha"].mean(),
    })


def main():
    cc = pd.read_csv(D / "country-codes.csv")
    countries = cc.rename(columns={"ISO3166-1-Alpha-3": "iso3", "CLDR display name": "name",
                                   "Region Name": "region", "Sub-region Name": "subregion"})[
        ["iso3", "name", "region", "subregion"]].dropna(subset=["iso3"])

    cy = pd.read_csv(D / "cereal_crop_yield_vs_fertilizer_application.csv").rename(columns={
        "Code": "iso3", "Year": "year", "Cereal yield (tonnes per hectare)": "cereal_t_ha",
        "Nitrogen fertilizer use (kilograms per hectare)": "n_kg_ha"})
    cy = cy[cy["iso3"].isin(countries["iso3"])][["iso3", "year", "cereal_t_ha", "n_kg_ha"]]

    pop = pd.read_csv(D / "population.csv").rename(columns={
        "Country Code": "iso3", "Year": "year", "Value": "population"})[["iso3", "year", "population"]]
    pop = pop[pop["iso3"].isin(countries["iso3"])]

    stats = cy.groupby("iso3").apply(yield_stats, include_groups=False)
    if isinstance(stats, pd.Series):          # pandas returns a Series when groups vary in length
        stats = stats.unstack()
    stats = stats.dropna(subset=["yield_2014_18_t_ha"]).reset_index()

    DB.unlink(missing_ok=True)
    with sqlite3.connect(DB) as con:
        countries.to_sql("countries", con, index=False)
        cy.to_sql("cereal_yield", con, index=False)
        pop.to_sql("population", con, index=False)
        stats.to_sql("cereal_stats", con, index=False)
        wb = D / "worldbank_indicators.csv"
        if wb.exists():
            pd.read_csv(wb).to_sql("wb_indicators", con, index=False)
            print("Loaded World Bank indicators from", wb.name)
        for t in ["countries", "cereal_yield", "population", "cereal_stats"]:
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"{t:14s} {n:6d} rows")


if __name__ == "__main__":
    main()
