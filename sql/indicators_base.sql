-- Production-side risk indicators per country.
-- Each indicator is converted to a percentile rank (0 = lowest risk, 1 = highest risk)
-- so that indicators with different units can be averaged into a transparent composite.

DROP VIEW IF EXISTS pop_growth;
CREATE VIEW pop_growth AS
SELECT p1.iso3,
       100.0 * (POWER(1.0 * p2.population / p1.population, 1.0 / 10) - 1) AS pop_growth_pct_yr
FROM population p1
JOIN population p2 ON p1.iso3 = p2.iso3 AND p1.year = 2015 AND p2.year = 2025;

DROP VIEW IF EXISTS indicators;
CREATE VIEW indicators AS
WITH base AS (
    SELECT c.iso3, c.name, c.region, c.subregion,
           s.yield_2014_18_t_ha, s.yield_trend_pct_yr, s.yield_volatility_cv_pct,
           s.n_use_2013_17_kg_ha, g.pop_growth_pct_yr
    FROM countries c
    JOIN cereal_stats s ON s.iso3 = c.iso3
    JOIN pop_growth  g ON g.iso3 = c.iso3
),
ranked AS (
    SELECT *,
           PERCENT_RANK() OVER (ORDER BY yield_2014_18_t_ha DESC)    AS r_low_yield,
           PERCENT_RANK() OVER (ORDER BY yield_trend_pct_yr DESC)    AS r_stagnation,
           PERCENT_RANK() OVER (ORDER BY yield_volatility_cv_pct ASC) AS r_volatility,
           PERCENT_RANK() OVER (ORDER BY pop_growth_pct_yr ASC)      AS r_pop_pressure
    FROM base
)
SELECT *,
       (r_low_yield + r_stagnation + r_volatility + r_pop_pressure) / 4.0 AS risk_index
FROM ranked;
