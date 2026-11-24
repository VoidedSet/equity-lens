-- Latest annual KPI comparison across all 5 hotel companies + derived interest coverage.
WITH ranked_annual AS (
  SELECT
    company_id,
    period,
    metric,
    value,
    yoy_change,
    ROW_NUMBER() OVER (PARTITION BY company_id, metric ORDER BY period DESC) AS rn
  FROM equity_lens.financials
  WHERE period_type = 'annual'
    AND period LIKE 'FY%'
),
latest AS (
  SELECT
    company_id,
    MAX(CASE WHEN metric = 'revenue' THEN period END) AS latest_period,
    MAX(CASE WHEN metric = 'revenue' THEN value END) AS revenue_cr,
    MAX(CASE WHEN metric = 'revenue' THEN yoy_change END) AS revenue_yoy_pct,
    MAX(CASE WHEN metric = 'operating_profit' THEN value END) AS operating_profit_cr,
    MAX(CASE WHEN metric = 'opm' THEN value END) AS opm_pct,
    MAX(CASE WHEN metric = 'net_profit' THEN value END) AS net_profit_cr,
    MAX(CASE WHEN metric = 'interest' THEN value END) AS interest_cr,
    MAX(CASE WHEN metric = 'borrowings' THEN value END) AS borrowings_cr,
    MAX(CASE WHEN metric = 'revpar' THEN value END) AS revpar_inr
  FROM ranked_annual
  WHERE rn = 1
  GROUP BY company_id
)
SELECT
  company_id,
  latest_period,
  revenue_cr,
  revenue_yoy_pct,
  operating_profit_cr,
  opm_pct,
  net_profit_cr,
  borrowings_cr,
  revpar_inr,
  ROUND(operating_profit_cr / NULLIF(interest_cr, 0), 2) AS interest_coverage
FROM latest
ORDER BY revenue_cr DESC NULLS LAST;
