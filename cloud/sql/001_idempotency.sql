-- Idempotency & canonical company migration for EquityLens AI Supabase serving tier.
-- Run in Supabase SQL Editor after schema.sql.

-- 1. Ensure canonical 5th company JUNIPER exists alongside existing companies.
INSERT INTO companies (id, name, ticker_nse, segment, strategy, brands, key_markets)
VALUES (
  'JUNIPER',
  'Juniper Hotels Ltd',
  'JUNIPER',
  'luxury_upper_upscale',
  'asset_heavy',
  ARRAY['Grand Hyatt', 'Andaz', 'Hyatt Regency', 'Hyatt Place'],
  ARRAY['Mumbai', 'Delhi', 'Ahmedabad', 'Lucknow']
)
ON CONFLICT (id) DO NOTHING;

-- 2. Add deterministic record_id / doc_id columns and unique indexes for upsert idempotency.
ALTER TABLE financials ADD COLUMN IF NOT EXISTS record_id TEXT;
ALTER TABLE financials ADD COLUMN IF NOT EXISTS doc_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_financials_record_id ON financials(record_id);

ALTER TABLE guidance_claims ADD COLUMN IF NOT EXISTS record_id TEXT;
ALTER TABLE guidance_claims ADD COLUMN IF NOT EXISTS doc_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_guidance_claims_record_id ON guidance_claims(record_id);

ALTER TABLE risk_flags ADD COLUMN IF NOT EXISTS record_id TEXT;
ALTER TABLE risk_flags ADD COLUMN IF NOT EXISTS doc_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_risk_flags_record_id ON risk_flags(record_id);

ALTER TABLE credit_ratings ADD COLUMN IF NOT EXISTS record_id TEXT;
ALTER TABLE credit_ratings ADD COLUMN IF NOT EXISTS doc_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_ratings_record_id ON credit_ratings(record_id);

ALTER TABLE raw_data ADD COLUMN IF NOT EXISTS record_id TEXT;
ALTER TABLE raw_data ADD COLUMN IF NOT EXISTS doc_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_data_record_id ON raw_data(record_id);

ALTER TABLE deviation_tracker ADD COLUMN IF NOT EXISTS record_id TEXT;
ALTER TABLE deviation_tracker ADD COLUMN IF NOT EXISTS doc_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_deviation_tracker_record_id ON deviation_tracker(record_id);

-- 3. Add deterministic chunk_id / doc_id to document_chunks and allow announcement/credit_rating chunks.
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_id TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS doc_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_chunk_id ON document_chunks(chunk_id);

ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_document_type_check;
ALTER TABLE document_chunks ADD CONSTRAINT document_chunks_document_type_check
  CHECK (document_type IN (
    'transcript', 'annual_report', 'quarterly_results',
    'investor_presentation', 'announcement', 'credit_rating'
  ));
