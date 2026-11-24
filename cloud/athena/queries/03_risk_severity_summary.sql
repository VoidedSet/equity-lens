-- Risk flag distribution across companies, categories, and severities.
SELECT
  company_id,
  category,
  severity,
  COUNT(*) AS flag_count,
  MIN(period) AS earliest_period,
  MAX(period) AS latest_period
FROM equity_lens.risk_flags
GROUP BY company_id, category, severity
ORDER BY
  company_id,
  CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END,
  flag_count DESC;
