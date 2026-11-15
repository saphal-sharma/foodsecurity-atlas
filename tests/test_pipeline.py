"""Tests for the World Bank parser and the full SQL indicator view.

The World Bank rows below are a small MADE-UP fixture used only to test the code path;
they are not real statistics.
"""
import shutil
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fetch_worldbank import parse  # noqa: E402

FIXTURE = [
    {"page": 1, "pages": 1},
    [
        {"indicator": {"id": "SN.ITK.DEFC.ZS"}, "countryiso3code": "NPL", "date": "2022", "value": 5.0},
        {"indicator": {"id": "SN.ITK.DEFC.ZS"}, "countryiso3code": "NPL", "date": "2021", "value": 6.0},
        {"indicator": {"id": "SN.ITK.DEFC.ZS"}, "countryiso3code": "", "date": "2022", "value": 9.9},
        {"indicator": {"id": "AG.LND.PRCP.MM"}, "countryiso3code": "NPL", "date": "2020", "value": 1500.0},
    ],
]


def test_parse_drops_aggregates_without_iso3():
    df = parse(FIXTURE)
    assert len(df) == 3
    assert set(df["indicator"]) == {"SN.ITK.DEFC.ZS", "AG.LND.PRCP.MM"}


def test_parse_handles_empty_response():
    assert parse([{"message": "error"}]).empty


def test_full_sql_uses_latest_year(tmp_path):
    db = tmp_path / "atlas.db"
    shutil.copy(ROOT / "data" / "atlas.db", db)
    with sqlite3.connect(db) as con:
        parse(FIXTURE).to_sql("wb_indicators", con, index=False)
        con.executescript((ROOT / "sql" / "indicators_full.sql").read_text())
        df = pd.read_sql("SELECT * FROM indicators", con)
    npl = df[df["iso3"] == "NPL"].iloc[0]
    assert npl["undernourishment_pct"] == 5.0          # latest year (2022) is used
    assert npl["undernourishment_year"] == 2022
    assert 0 <= npl["risk_index"] <= 1
    assert df["risk_index"].between(0, 1).all()
