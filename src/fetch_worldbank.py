"""Download hunger and rainfall indicators from the World Bank API (needs internet).

Indicators
  SN.ITK.DEFC.ZS   Prevalence of undernourishment (% of population), FAO via World Bank
  AG.LND.PRCP.MM   Average precipitation in depth (mm per year)

Saves data/worldbank_indicators.csv with columns iso3, indicator, year, value.
Then rerun:  python src/build_database.py && python src/make_map.py
"""
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parents[1] / "data" / "worldbank_indicators.csv"
INDICATORS = ["SN.ITK.DEFC.ZS", "AG.LND.PRCP.MM"]
URL = "https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000&date=2000:2025"


def parse(payload) -> pd.DataFrame:
    """Turn a World Bank API JSON response into tidy rows."""
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["iso3", "indicator", "year", "value"])
    rows = [{"iso3": r.get("countryiso3code"), "indicator": r["indicator"]["id"],
             "year": int(r["date"]), "value": r["value"]}
            for r in payload[1] if r.get("countryiso3code")]
    return pd.DataFrame(rows)


def main():
    frames = []
    for ind in INDICATORS:
        r = requests.get(URL.format(ind=ind), timeout=120)
        r.raise_for_status()
        df = parse(r.json())
        print(f"{ind}: {df['value'].notna().sum()} values")
        frames.append(df)
    pd.concat(frames).to_csv(OUT, index=False)
    print("Saved", OUT)


if __name__ == "__main__":
    main()
