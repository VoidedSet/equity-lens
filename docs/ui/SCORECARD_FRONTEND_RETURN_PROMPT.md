# Return Prompt - Scorecard Frontend Reference

Copy this prompt in a new chat when you return.

---

You are continuing work on EquityLens AI in this repository.

Goal:
Implement and maintain the frontend scorecard display using the latest deep analytics structure from Supabase scorecards.evidence_summary, with strict source citation rendering.

Non-negotiable rules:
1. Every analytical statement shown on UI must have a citation reference from evidence_summary.citation_graph.
2. If citation is missing for a displayed claim, hide that claim and show DATA NOT AVAILABLE.
3. Do not invent values. Render only what exists in API payload.
4. Keep existing visual style and components unless a change is required.

Data contract to use:
- Top-level scorecard fields:
  - dim_credibility
  - dim_financial_quality
  - dim_industry_position
  - dim_risk
  - composite_score
  - confidence_level
- Deep fields in evidence_summary:
  - dimension_scores
    - industry_position
    - financial_quality
    - management_credibility
    - risk_identification
    - stress_test_resilience
    - delivery_credibility
  - decomposition
    - financial_quality
    - industry_position
    - management_credibility
    - risk_identification
  - stress_test
    - summary
      - base_icr
      - weighted_stressed_icr
      - breach_probability_icr_lt_1_5
      - matrix[]
    - assumptions
  - forward_risk
    - next_2q_margin_compression_prob
    - next_2q_guidance_miss_prob
    - next_2q_liquidity_stress_prob
  - peer_normalized
    - dimensions[dimension_name]
      - value
      - peer_mean
      - peer_std
      - z_score
      - percentile
      - rank
      - total
  - uncertainty
    - composite
    - band_low
    - band_high
    - band_width
    - confidence_level
  - citation_graph
    - financial_quality[]
    - industry_position[]
    - management_credibility[]
    - risk_identification[]
    - stress_test_resilience[]

Frontend requirements:
1. Scorecard block must render 5 core dimensions:
   - Industry Position
   - Financial Quality
   - Management Credibility
   - Risk Identification
   - Stress-Test Resilience
2. Show composite score and uncertainty band as:
   - Composite: X
   - Range: band_low to band_high
3. Show peer context for composite and each dimension:
   - percentile, rank, z_score
4. Show forward risk probabilities as percentages in a separate "Early Warning" section.
5. Show stress matrix table (3x3) with demand_scenario x rate_scenario and stressed_icr/cell_score.
6. For each displayed section, wire a citation trigger (existing Citation component or equivalent) using citation_graph items.

Citation rendering behavior:
- Use citation_graph.<dimension> entries to open SourceModal.
- Render at least one citation link near each claim/metric shown.
- Prefer nearest matching citation by metric/category/dimension.
- If no citation exists for that specific displayed value, do not render value-level claim text; show DATA NOT AVAILABLE.

Implementation checklist:
1. Update API types and transforms so evidence_summary is strongly typed and passed to UI.
2. Update scorecard component props to include deep evidence_summary fields.
3. Add new sub-sections:
   - Decomposition
   - Stress Matrix
   - Forward Risk
   - Peer-Normalized View
   - Uncertainty Band
4. Add citation links in each subsection.
5. Validate UI with one company and all companies compare path.
6. Keep backward compatibility if old scorecard row lacks deep fields.

When you execute:
- First inspect current files under ui/src/components, ui/src/lib/hooks.ts, ui/src/lib/transforms.ts, and ui/src/app/api/data/company/[id]/route.ts.
- Then implement minimal safe edits.
- Run typecheck/build and report any residual issues.

Output expectations:
- Return a short summary of files changed.
- List where citations were added.
- Mention any fields still unavailable from backend.

---

Quick validation query after implementation:
- "Show IHCL scorecard with decomposition, stress matrix, peer percentile, uncertainty, and citations for every displayed analytical claim."
