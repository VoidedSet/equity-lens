-- Management guidance credibility scorecard & beat/miss distribution per company.
SELECT
  c.company_id,
  c.overall_score,
  c.hit_rate,
  c.avg_deviation,
  c.consecutive_misses,
  c.trend,
  c.total_matched_count,
  COUNT(CASE WHEN d.flag = 'BEAT' THEN 1 END) AS beats,
  COUNT(CASE WHEN d.flag = 'IN-LINE' THEN 1 END) AS in_lines,
  COUNT(CASE WHEN d.flag = 'MISS' THEN 1 END) AS misses
FROM equity_lens.credibility_scores c
LEFT JOIN equity_lens.deviation_tracker d
  ON c.company_id = d.company_id
GROUP BY
  c.company_id,
  c.overall_score,
  c.hit_rate,
  c.avg_deviation,
  c.consecutive_misses,
  c.trend,
  c.total_matched_count
ORDER BY c.overall_score DESC;
