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
    buttons = [dict(label=label, method="update", args=[{"visible": [j == i for j in range(len(layers))]}])
               for i, (_, label, _, _) in enumerate(layers)]
    fig.update_traces(colorbar=dict(orientation="h", x=0.5, xanchor="center", y=-0.02, yanchor="top",
                                    thickness=12, len=0.8, title_side="top"))
    fig.update_layout(
        updatemenus=[dict(buttons=buttons, direction="down", x=0.0, y=1.0, xanchor="left", yanchor="bottom")],
        geo=dict(showframe=False, showcoastlines=False, projection_type="natural earth",
                 projection_rotation=dict(lon=10), lataxis_range=[-58, 84], bgcolor="rgba(0,0,0,0)"),
        autosize=True, height=560, margin=dict(l=0, r=0, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
    fig.write_html(OUT / "atlas.html", include_plotlyjs="cdn", config={"responsive": True})
    write_page(fig, df)

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


def write_page(fig, df):
    """Website version (docs/index.html): short explanation, the map and the key results."""
    reg = df.groupby("region")[["risk_index", "yield_2014_18_t_ha", "pop_growth_pct_yr"]].median().round(2)
    reg = reg.sort_values("risk_index", ascending=False)
    top = df.sort_values("risk_index", ascending=False).head(5)
    rows = "".join(f"<tr><td>{r}</td><td>{v.risk_index:.2f}</td><td>{v.yield_2014_18_t_ha:.2f}</td><td>{v.pop_growth_pct_yr:.2f}</td></tr>"
                   for r, v in reg.iterrows())
    mapdiv = fig.to_html(full_html=False, include_plotlyjs="cdn", config={"responsive": True, "displaylogo": False})
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FoodSecurity Atlas</title>
<style>
:root {{ --bg:#f7f5f0; --ink:#222; --muted:#5f6368; --line:#e2ded4; --accent:#a8361f; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }}
.wrap {{ max-width:1100px; margin:0 auto; padding:0 18px; }}
header {{ padding:26px 0 6px; }} h1 {{ font-family:Georgia,serif; font-size:30px; margin:0 0 6px; }}
.lede {{ color:var(--muted); max-width:70ch; margin:0; }}
.summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin:16px 0; }}
.summary div {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:10px 12px; font-size:14.5px; }}
.summary b {{ display:block; font-size:12px; text-transform:uppercase; letter-spacing:.05em; color:var(--accent); }}
.map {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:6px; }}
table {{ border-collapse:collapse; width:100%; max-width:640px; font-size:14.5px; }}
th,td {{ padding:6px 8px; border-bottom:1px solid var(--line); text-align:right; }} th:first-child,td:first-child {{ text-align:left; }}
th {{ font-size:12px; color:var(--muted); text-transform:uppercase; }}
h2 {{ font-family:Georgia,serif; font-size:21px; margin:26px 0 8px; }}
p.small {{ font-size:14px; color:var(--muted); max-width:72ch; }}
footer {{ padding:24px 0 36px; color:var(--muted); font-size:13px; }}
a {{ color:var(--accent); }}
</style></head><body><div class="wrap">
<header><h1>FoodSecurity Atlas</h1>
<p class="lede">Where is food production most at risk? This map combines cereal yields, yield trends, harvest volatility and population growth for 176 countries into one transparent risk index. Choose a layer in the menu and hover over or tap a country.</p></header>
<div class="summary">
<div><b>Question</b>Which countries face the highest risk to their own cereal supply?</div>
<div><b>Answer</b>Africa's median risk (0.68) is almost twice Europe's (0.36). Highest: {", ".join(top["name"])}.</div>
<div><b>Method</b>Each indicator ranked across countries in SQL (PERCENT_RANK), then averaged with equal weights.</div>
</div>
<div class="map">{mapdiv}</div>
<h2>Median by region</h2>
<div style="overflow-x:auto"><table><thead><tr><th>Region</th><th>Risk index</th><th>Cereal yield (t/ha)</th><th>Population growth (%/yr)</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="small">The index measures risk to domestic cereal production, not hunger itself. A few countries with small, rainfed cereal sectors but little hunger rank high because their yields are low and volatile. Equal weights are a simplification; they can be changed in the SQL files.</p>
<footer>Data: FAO via Our World in Data; World Bank. Code and method: <a href="https://github.com/saphal-sharma/foodsecurity-atlas">github.com/saphal-sharma/foodsecurity-atlas</a>. Built by Saphal Sharma.</footer>
</div></body></html>"""
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(html)


if __name__ == "__main__":
    main()
