-- ============================================================
-- EQUITYLENS AI — SUPABASE SCHEMA
-- Run this entire file in your Supabase SQL Editor
-- Every row is cited: [Document | Page | Period]
-- vector(384) = all-MiniLM-L6-v2 embedding dimension
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════════════════════════════════
-- COMPANIES master table
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS companies (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  ticker_nse TEXT,
  segment TEXT,
  strategy TEXT,
  brands TEXT[],
  key_markets TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO companies VALUES
  ('IHCL', 'Indian Hotels Company Ltd', 'INDHOTEL', 'premium_luxury', 'hybrid',
   ARRAY['Taj', 'Vivanta', 'SeleQtions', 'Ginger'],
   ARRAY['Mumbai', 'Delhi', 'Bengaluru', 'Goa']),
  ('CHALET', 'Chalet Hotels Ltd', 'CHALET', 'upper_midscale', 'asset_heavy',
   ARRAY['Marriott', 'Westin', 'Renaissance', 'Four Points'],
   ARRAY['Mumbai', 'Bengaluru', 'Hyderabad']),
  ('LEMONTREE', 'Lemon Tree Hotels Ltd', 'LEMONTREE', 'economy_midscale', 'hybrid',
   ARRAY['Lemon Tree Premier', 'Lemon Tree', 'Red Fox', 'Keys'],
   ARRAY['Delhi-NCR', 'Hyderabad', 'Pune', 'Bengaluru']),
  ('EIH', 'EIH Ltd (Oberoi Group)', 'EIHOTEL', 'premium_luxury', 'asset_heavy',
   ARRAY['Oberoi', 'Trident'],
   ARRAY['Delhi', 'Mumbai', 'Udaipur', 'Agra']),
  ('ITCHOTELS', 'ITC Hotels Ltd', 'ITCHOTELS', 'premium_luxury', 'asset_heavy',
   ARRAY['ITC Grand', 'Welcomhotel', 'Mementos', 'Storii'],
   ARRAY['Delhi', 'Bengaluru', 'Chennai', 'Kolkata'])
ON CONFLICT (id) DO NOTHING;

-- ═══════════════════════════════════════════════════════════
-- TABLE A: Time-Series Financials
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS financials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  period TEXT NOT NULL,
  period_type TEXT CHECK (period_type IN ('quarterly', 'annual')),
  metric TEXT NOT NULL,
  value FLOAT,
  unit TEXT,
  yoy_change FLOAT,
  source_document TEXT NOT NULL,
  source_page INT,
  source_timestamp TEXT,
  period_label TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fin_company  ON financials(company_id);
CREATE INDEX IF NOT EXISTS idx_fin_period   ON financials(period);
CREATE INDEX IF NOT EXISTS idx_fin_metric   ON financials(metric);

-- ═══════════════════════════════════════════════════════════
-- TABLE B: Management Guidance Claims
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS guidance_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  statement_quarter TEXT,
  statement_date DATE,
  target_period TEXT,
  metric_type TEXT NOT NULL,
  guidance_value_low FLOAT,
  guidance_value_high FLOAT,
  guidance_value_point FLOAT,
  unit TEXT,
  verbatim_quote TEXT NOT NULL,
  confidence_language TEXT,
  speaker TEXT,
  check_type TEXT,
  source_document TEXT NOT NULL,
  source_page INT,
  source_timestamp TEXT,
  extracted_at TIMESTAMPTZ DEFAULT NOW(),
  verified BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_guid_company ON guidance_claims(company_id);
CREATE INDEX IF NOT EXISTS idx_guid_check   ON guidance_claims(check_type);

-- ═══════════════════════════════════════════════════════════
-- TABLE C: Deviation Tracker (Said vs Delivered)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS deviation_tracker (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  guidance_id UUID REFERENCES guidance_claims(id),
  actual_metric_id UUID REFERENCES financials(id),
  company_id TEXT NOT NULL,
  period TEXT NOT NULL,
  metric_type TEXT NOT NULL,
  check_type TEXT,
  guided_value FLOAT,
  actual_value FLOAT,
  delta FLOAT,
  delta_pct FLOAT,
  flag TEXT CHECK (flag IN ('BEAT', 'MISS', 'IN-LINE')),
  severity TEXT CHECK (severity IN ('none', 'minor', 'moderate', 'major', 'critical')),
  pattern TEXT,
  insight TEXT,
  source_guidance TEXT NOT NULL,
  source_actual TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dev_company ON deviation_tracker(company_id);
CREATE INDEX IF NOT EXISTS idx_dev_flag    ON deviation_tracker(flag);

-- ═══════════════════════════════════════════════════════════
-- TABLE D: Risk Flags
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS risk_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  category TEXT CHECK (category IN (
    'debt', 'governance', 'operational', 'regulatory',
    'auditor', 'supply_overhang', 'margin_compression',
    'management_mismatch', 'key_person'
  )),
  check_type TEXT,
  description TEXT NOT NULL,
  severity TEXT CHECK (severity IN ('critical', 'high', 'medium')),
  subcategory TEXT,
  related_credit_rating_id UUID,
  verbatim_quote TEXT,
  source_document TEXT NOT NULL,
  source_page INT,
  period TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_company  ON risk_flags(company_id);
CREATE INDEX IF NOT EXISTS idx_risk_category ON risk_flags(category);

-- ═══════════════════════════════════════════════════════════
-- TABLE E: Raw Data (qualitative catch-all)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS raw_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  data_type TEXT,
  category TEXT,
  key_name TEXT,
  value_text TEXT,
  value_numeric FLOAT,
  unit TEXT,
  context TEXT,
  source_document TEXT NOT NULL,
  source_page INT,
  source_timestamp TEXT,
  period TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_company ON raw_data(company_id);
CREATE INDEX IF NOT EXISTS idx_raw_type    ON raw_data(data_type);

-- ═══════════════════════════════════════════════════════════
-- TABLE F: Credibility Scores
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS credibility_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  period TEXT NOT NULL,
  overall_score FLOAT,
  check_1_revpar_score FLOAT,
  check_2_keys_score FLOAT,
  check_3_driver_score FLOAT,
  check_4_fnb_score FLOAT,
  check_5_debt_score FLOAT,
  check_6_supply_score FLOAT,
  hit_rate FLOAT,
  avg_deviation FLOAT,
  total_guidance_count INT,
  total_matched_count INT,
  consecutive_misses INT,
  trend TEXT CHECK (trend IN ('improving', 'stable', 'declining')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(company_id, period)
);

-- ═══════════════════════════════════════════════════════════
-- TABLE G: 4-Dimension Scorecards
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scorecards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  period TEXT NOT NULL,
  dim_credibility FLOAT,
  dim_financial_quality FLOAT,
  dim_industry_position FLOAT,
  dim_risk FLOAT,
  composite_score FLOAT,
  confidence_level TEXT CHECK (confidence_level IN ('high', 'medium', 'low')),
  evidence_summary JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(company_id, period)
);

-- ═══════════════════════════════════════════════════════════
-- TABLE H: Document Chunks + pgvector Embeddings (RAG)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  document_type TEXT CHECK (document_type IN (
    'transcript', 'annual_report', 'quarterly_results', 'investor_presentation'
  )),
  period TEXT,
  chunk_text TEXT NOT NULL,
  chunk_index INT,
  section_name TEXT,
  source_document TEXT NOT NULL,
  source_page INT,
  speaker TEXT,
  embedding vector(384),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_company ON document_chunks(company_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc     ON document_chunks(source_document);

-- ivfflat index for fast cosine similarity search
-- (run AFTER populating data for best performance)
-- CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ═══════════════════════════════════════════════════════════
-- TABLE I: Credit Ratings
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS credit_ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  rating_agency TEXT NOT NULL,
  rating_scale TEXT,
  rating_outlook TEXT,
  instrument TEXT,
  rating_date DATE,
  rating_amount_crores FLOAT,
  previous_rating TEXT,
  watch_status TEXT,
  rationale TEXT,
  source_document TEXT NOT NULL,
  source_page INT,
  period TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ratings_company ON credit_ratings(company_id);
CREATE INDEX IF NOT EXISTS idx_ratings_date    ON credit_ratings(rating_date);

-- ═══════════════════════════════════════════════════════════
-- TABLE J: Document Registry (tracks every ingested file)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL REFERENCES companies(id),
  document_name TEXT NOT NULL,
  document_type TEXT CHECK (document_type IN (
    'annual_report', 'quarterly_results', 'transcript',
    'investor_presentation', 'announcement'
  )),
  period TEXT,
  release_date DATE,
  file_format TEXT,
  file_path TEXT,
  file_size_bytes INT,
  source_url TEXT,
  extraction_status TEXT CHECK (extraction_status IN (
    'raw', 'extracted', 'processed', 'failed'
  )) DEFAULT 'raw',
  extraction_logs JSONB,
  chunks_count INT DEFAULT 0,
  guidance_count INT DEFAULT 0,
  risk_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(company_id, document_name)
);

CREATE INDEX IF NOT EXISTS idx_docs_company ON documents(company_id);
CREATE INDEX IF NOT EXISTS idx_docs_type    ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_docs_status  ON documents(extraction_status);

-- ═══════════════════════════════════════════════════════════
-- pgvector similarity search function
-- ═══════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(384),
  match_count INT DEFAULT 5,
  filter_company TEXT DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  company_id TEXT,
  document_type TEXT,
  period TEXT,
  chunk_text TEXT,
  source_document TEXT,
  source_page INT,
  speaker TEXT,
  section_name TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id, dc.company_id, dc.document_type, dc.period,
    dc.chunk_text, dc.source_document, dc.source_page,
    dc.speaker, dc.section_name,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM document_chunks dc
  WHERE (filter_company IS NULL OR dc.company_id = filter_company)
    AND dc.embedding IS NOT NULL
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END; $$;
