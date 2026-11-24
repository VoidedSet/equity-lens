-- Athena / AWS Glue Data Catalog external table definitions for S3 curated/ Parquet tables.
-- Replace ${S3_BUCKET} with your target S3 bucket name before executing in Athena Query Editor.

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.financials (
  record_id STRING,
  doc_id STRING,
  period STRING,
  metric STRING,
  value DOUBLE,
  unit STRING,
  yoy_change DOUBLE,
  source_document STRING,
  source_page INT,
  source_timestamp STRING,
  period_label STRING,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING,
  period_type STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/financials/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'projection.period_type.type' = 'enum',
  'projection.period_type.values' = 'annual,quarterly',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/financials/company_id=${company_id}/period_type=${period_type}/'
);

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.guidance_claims (
  record_id STRING,
  doc_id STRING,
  statement_quarter STRING,
  statement_date STRING,
  target_period STRING,
  metric_type STRING,
  guidance_value_low DOUBLE,
  guidance_value_high DOUBLE,
  guidance_value_point DOUBLE,
  unit STRING,
  verbatim_quote STRING,
  confidence_language STRING,
  speaker STRING,
  check_type STRING,
  source_document STRING,
  source_page INT,
  source_timestamp STRING,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/guidance_claims/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/guidance_claims/company_id=${company_id}/'
);

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.risk_flags (
  record_id STRING,
  doc_id STRING,
  period STRING,
  category STRING,
  check_type STRING,
  description STRING,
  severity STRING,
  subcategory STRING,
  verbatim_quote STRING,
  source_document STRING,
  source_page INT,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/risk_flags/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/risk_flags/company_id=${company_id}/'
);

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.credit_ratings (
  record_id STRING,
  doc_id STRING,
  period STRING,
  rating_agency STRING,
  rating_scale STRING,
  rating_outlook STRING,
  instrument STRING,
  rating_date STRING,
  rating_amount_crores DOUBLE,
  previous_rating STRING,
  watch_status STRING,
  rationale STRING,
  source_document STRING,
  source_page INT,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/credit_ratings/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/credit_ratings/company_id=${company_id}/'
);

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.raw_data (
  record_id STRING,
  doc_id STRING,
  period STRING,
  data_type STRING,
  category STRING,
  key_name STRING,
  value_text STRING,
  value_numeric DOUBLE,
  unit STRING,
  context STRING,
  source_document STRING,
  source_page INT,
  source_timestamp STRING,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/raw_data/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/raw_data/company_id=${company_id}/'
);

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.document_chunks (
  chunk_id STRING,
  doc_id STRING,
  period STRING,
  chunk_index INT,
  section_name STRING,
  source_document STRING,
  source_page INT,
  speaker STRING,
  source_timestamp STRING,
  chunk_text STRING,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING,
  document_type STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/document_chunks/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'projection.document_type.type' = 'enum',
  'projection.document_type.values' = 'annual_report,transcript,quarterly_results,investor_presentation,announcement,credit_rating',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/document_chunks/company_id=${company_id}/document_type=${document_type}/'
);

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.deviation_tracker (
  record_id STRING,
  guidance_record_id STRING,
  actual_record_id STRING,
  period STRING,
  metric_type STRING,
  check_type STRING,
  guided_value DOUBLE,
  actual_value DOUBLE,
  delta DOUBLE,
  delta_pct DOUBLE,
  flag STRING,
  severity STRING,
  pattern STRING,
  insight STRING,
  source_guidance STRING,
  source_actual STRING,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/deviation_tracker/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/deviation_tracker/company_id=${company_id}/'
);

CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens.credibility_scores (
  record_id STRING,
  period STRING,
  overall_score DOUBLE,
  check_1_revpar_score DOUBLE,
  check_2_keys_score DOUBLE,
  check_3_driver_score DOUBLE,
  check_4_fnb_score DOUBLE,
  check_5_debt_score DOUBLE,
  check_6_supply_score DOUBLE,
  hit_rate DOUBLE,
  avg_deviation DOUBLE,
  total_guidance_count INT,
  total_matched_count INT,
  consecutive_misses INT,
  trend STRING,
  ingested_at STRING
)
PARTITIONED BY (
  company_id STRING
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/curated/credibility_scores/'
TBLPROPERTIES (
  'parquet.compression' = 'SNAPPY',
  'projection.enabled' = 'true',
  'projection.company_id.type' = 'enum',
  'projection.company_id.values' = 'IHCL,CHALET,LEMONTREE,EIH,JUNIPER',
  'storage.location.template' = 's3://${S3_BUCKET}/curated/credibility_scores/company_id=${company_id}/'
);
