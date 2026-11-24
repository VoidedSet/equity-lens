-- Period-by-period guidance vs actual deviation trends and consecutive patterns.
SELECT
  company_id,
  period,
  metric_type,
  check_type,
  guided_value,
  actual_value,
  delta,
  delta_pct,
  flag,
  severity,
  pattern,
  source_guidance,
  source_actual
FROM equity_lens.deviation_tracker
ORDER BY company_id, period DESC, ABS(COALESCE(delta_pct, 0)) DESC;
