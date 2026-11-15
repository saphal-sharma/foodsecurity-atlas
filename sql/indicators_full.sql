-- Full indicator set: production risk plus hunger and rainfall from the World Bank.
-- Requires the wb_indicators table created after running src/fetch_worldbank.py.

DROP VIEW IF EXISTS pop_growth;
CREATE VIEW pop_growth AS
SELECT p1.iso3,
       100.0 * (POWER(1.0 * p2.population / p1.population, 1.0 / 10) - 1) AS pop_growth_pct_yr
FROM population p1
JOIN population p2 ON p1.iso3 = p2.iso3 AND p1.year = 2015 AND p2.year = 2025;

DROP VIEW IF EXISTS latest_wb;
CREATE VIEW latest_wb AS
SELECT iso3, indicator, value, year
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY iso3, indicator ORDER BY year DESC) AS rn
      FROM wb_indicators WHERE value IS NOT NULL)
WHERE rn = 1;

DROP VIEW IF EXISTS indicators;
CREATE VIEW indicators AS
WITH base AS (
    SELECT c.iso3, c.name, c.region, c.subregion,
           s.yield_2014_18_t_ha, s.yield_trend_pct_yr, s.yield_volatility_cv_pct,
           s.n_use_2013_17_kg_ha, g.pop_growth_pct_yr,
           h.value AS undernourishment_pct, h.year AS undernourishment_year,
           r.value AS precipitation_mm_yr
    FROM countries c
    JOIN cereal_stats s ON s.iso3 = c.iso3
    JOIN pop_growth  g ON g.iso3 = c.iso3
    LEFT JOIN latest_wb h ON h.iso3 = c.iso3 AND h.indicator = 'SN.ITK.DEFC.ZS'
    LEFT JOIN latest_wb r ON r.iso3 = c.iso3 AND r.indicator = 'AG.LND.PRCP.MM'
),
ranked AS (
    SELECT *,
           PERCENT_RANK() OVER (ORDER BY yield_2014_18_t_ha DESC)    AS r_low_yield,
           PERCENT_RANK() OVER (ORDER BY yield_trend_pct_yr DESC)    AS r_stagnation,
           PERCENT_RANK() OVER (ORDER BY yield_volatility_cv_pct ASC) AS r_volatility,
           PERCENT_RANK() OVER (ORDER BY pop_growth_pct_yr ASC)      AS r_pop_pressure,
           CASE WHEN undernourishment_pct IS NULL THEN NULL
                ELSE PERCENT_RANK() OVER (PARTITION BY undernourishment_pct IS NULL
                                          ORDER BY undernourishment_pct ASC) END AS r_hunger,
           CASE WHEN precipitation_mm_yr IS NULL THEN NULL
                ELSE PERCENT_RANK() OVER (PARTITION BY precipitation_mm_yr IS NULL
                                          ORDER BY precipitation_mm_yr DESC) END AS r_dryness
    FROM base
)
SELECT *,
       (r_low_yield + r_stagnation + r_volatility + r_pop_pressure
        + COALESCE(r_hunger, 0) + COALESCE(r_dryness, 0))
       / (4.0 + (r_hunger IS NOT NULL) + (r_dryness IS NOT NULL)) AS risk_index
FROM ranked;
