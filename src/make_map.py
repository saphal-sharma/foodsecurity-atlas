"""Run the SQL indicator views and build the interactive atlas (results/atlas.html)."""
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "atlas.db"
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

LAYERS = [  # column, label, colour scale, reverse
    ("risk_index", "Composite risk index (0 = low, 1 = high)", "OrRd", False),
    ("yield_2014_18_t_ha", "Cereal yield 2014-18 (t/ha)", "YlGn", False),
    ("yield_trend_pct_yr", "Cereal yield trend 1999-2018 (%/yr)", "RdYlGn", False),
    ("yield_volatility_cv_pct", "Cereal yield volatility (CV %)", "Purples", False),
    ("pop_growth_pct_yr", "Population growth 2015-2025 (%/yr)", "Blues", False),
    ("undernourishment_pct", "Undernourishment (% of population)", "Reds", False),
    ("precipitation_mm_yr", "Average precipitation (mm/yr)", "Blues", False),
]


def main():
    with sqlite3.connect(DB) as con:
        has_wb = con.execute("SELECT name FROM sqlite_master WHERE name='wb_indicators'").fetchone()
        sql_file = "indicators_full.sql" if has_wb else "indicators_base.sql"
        con.executescript((ROOT / "sql" / sql_file).read_text())
        df = pd.read_sql("SELECT * FROM indicators", con)
    print(f"Used {sql_file}: {len(df)} countries")
    df.round(3).to_csv(OUT / "indicators.csv", index=False)

    layers = [l for l in LAYERS if l[0] in df.columns and df[l[0]].notna().any()]
    fig = go.Figure()
    for i, (col, label, scale, rev) in enumerate(layers):
        hover = (df["name"] + "<br>" + label + ": " + df[col].round(2).astype(str)
                 + "<br>Risk index: " + df["risk_index"].round(2).astype(str))
        fig.add_trace(go.Choropleth(
            locations=df["iso3"], z=df[col], text=hover, hoverinfo="text",
            colorscale=scale, reversescale=rev, visible=(i == 0),
            colorbar_title=label.split(" (")[0], marker_line_width=0.3))
    buttons = [dict(label=label, method="update",
                    args=[{"visible": [j == i for j in range(len(layers))]},
                          {"title": f"FoodSecurity Atlas: {label}"}])
               for i, (_, label, _, _) in enumerate(layers)]
    fig.update_layout(
        title=f"FoodSecurity Atlas: {layers[0][1]}",
        updatemenus=[dict(buttons=buttons, direction="down", x=0.01, y=1.08, xanchor="left")],
        geo=dict(showframe=False, projection_type="natural earth"),
        height=620, margin=dict(l=10, r=10, t=90, b=10),
        annotations=[dict(text="Data: FAO via Our World in Data; World Bank. Method: README.",
                          x=0, y=-0.02, xref="paper", yref="paper", showarrow=False, font_size=10)])
    fig.write_html(OUT / "atlas.html", include_plotlyjs="cdn")

    top = df.sort_values("risk_index", ascending=False).head(15)[
        ["name", "region", "risk_index", "yield_2014_18_t_ha", "yield_trend_pct_yr",
         "yield_volatility_cv_pct", "pop_growth_pct_yr"]].round(2)
    top.to_csv(OUT / "top15_risk.csv", index=False)
    reg = df.groupby("region")[["risk_index", "yield_2014_18_t_ha", "pop_growth_pct_yr"]].median().round(2)
    reg["countries"] = df.groupby("region").size()
    reg.to_csv(OUT / "risk_by_region.csv")
    pd.set_option("display.width", 200)
    print(top.to_string(index=False))
    print(reg)


if __name__ == "__main__":
    main()
