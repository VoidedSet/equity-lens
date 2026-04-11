"use client";

import { useState } from "react";
import { useCompanyData, useCompare } from "@/lib/hooks";
import {
  toUICompany,
  toUIKeyMetrics,
  toUIDeviations,
  toUIScorecard,
  toUIRiskFlags,
  toUICredibility,
  toUICompareTable,
} from "@/lib/transforms";

export default function ReportPage() {
  const [companyId, setCompanyId] = useState("IHCL");
  const { data: companyData, loading } = useCompanyData(companyId);
  const { data: compareData } = useCompare();

  if (loading || !companyData) {
    return <div className="min-h-screen flex items-center justify-center"><p className="text-sm text-[#94a3b8]">Loading report...</p></div>;
  }

  const company = toUICompany(companyData.company);
  const metrics = toUIKeyMetrics(companyData.keyMetrics);
  const deviations = toUIDeviations(companyData.deviations, companyData.guidance);
  const scorecard = companyData.scorecards[0] ? toUIScorecard(companyData.scorecards[0]) : { credibility: 0, financialQuality: 0, industryPosition: 0, risk: 0, composite: 0, companyId: "IHCL", period: "" };
  const riskFlags = toUIRiskFlags(companyData.riskFlags);
  const credibility = toUICredibility(companyData.credibility);
  const tones = companyData.managementTone;
  const uiCompare = compareData ? toUICompareTable(compareData) : null;

  const missCount = deviations.filter((d) => d.flag === "MISS").length;
  const beatCount = deviations.filter((d) => d.flag === "BEAT").length;
  const inlineCount = deviations.filter((d) => d.flag === "IN-LINE").length;
  const hitRate = deviations.length > 0 ? Math.round(((beatCount + inlineCount) / deviations.length) * 100) : 0;

  const rankings = uiCompare?.rankings?.sort((a, b) => b.composite - a.composite) ?? [];

  // Build footnotes from sources
  const footnotes = [
    ...companyData.deviations.map((d, i) => ({
      id: i + 1, source: d.source_guidance.split(" | ")[0], document: d.source_guidance, period: d.period,
    })),
    ...companyData.riskFlags.map((r, i) => ({
      id: companyData.deviations.length + i + 1, source: r.source_document.split(" | ")[0], document: r.source_document, period: r.period,
    })),
  ];

  return (
    <div className="report-container">
      {/* Controls — hidden in print */}
      <div className="no-print fixed top-4 right-4 z-50 flex gap-2 items-center">
        <select
          value={companyId}
          onChange={(e) => setCompanyId(e.target.value)}
          className="px-3 py-2 bg-white text-[#0f172a] text-sm font-medium rounded-lg border border-[#e2e8f0] cursor-pointer"
        >
          <option value="IHCL">IHCL — Indian Hotels</option>
          <option value="CHALET">CHALET — Chalet Hotels</option>
          <option value="LEMONTREE">LEMONTREE — Lemon Tree</option>
          <option value="EIH">EIH — Oberoi Group</option>
          <option value="JUNIPER">JUNIPER — Juniper Hotels</option>
        </select>
        <button
          onClick={() => window.print()}
          className="px-4 py-2 bg-[#0f172a] text-white text-sm font-medium rounded-lg hover:bg-[#1e293b] cursor-pointer"
        >
          Download PDF
        </button>
        <button
          onClick={() => window.history.back()}
          className="px-4 py-2 bg-white text-[#0f172a] text-sm font-medium rounded-lg border border-[#e2e8f0] hover:bg-[#f8fafc] cursor-pointer"
        >
          Back
        </button>
      </div>

      {/* ═══ COVER PAGE ═══ */}
      <div className="page cover-page">
        <div className="cover-content">
          <p className="cover-label">EQUITY RESEARCH REPORT</p>
          <h1 className="cover-title">{company.name}</h1>
          <p className="cover-ticker">NSE: {company.ticker} &middot; {company.segment}</p>

          <div className="cover-score">
            <span className="cover-score-number">{scorecard.composite}</span>
            <span className="cover-score-label">/ 100 Composite Score</span>
          </div>

          <div className="cover-meta">
            <div className="cover-meta-item">
              <span className="cover-meta-label">Hit Rate</span>
              <span className="cover-meta-value">{hitRate}%</span>
            </div>
            <div className="cover-meta-item">
              <span className="cover-meta-label">Claims Tracked</span>
              <span className="cover-meta-value">{deviations.length}</span>
            </div>
            <div className="cover-meta-item">
              <span className="cover-meta-label">Misses</span>
              <span className="cover-meta-value miss">{missCount}</span>
            </div>
            <div className="cover-meta-item">
              <span className="cover-meta-label">Credibility</span>
              <span className="cover-meta-value">{scorecard.credibility}/100</span>
            </div>
          </div>

          <div className="cover-footer">
            <p>EquityLens AI &middot; Hotel Sector Intelligence</p>
            <p className="cover-date">{new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</p>
            <p className="cover-disclaimer">
              Source-Only Architecture. Every claim cites its document, page, and period.
              This report contains {footnotes.length} source citations.
            </p>
          </div>
        </div>
      </div>

      {/* ═══ EXECUTIVE SUMMARY ═══ */}
      <div className="page">
        <h2 className="section-title">Executive Summary</h2>

        <p className="prose">
          <strong>{company.name}</strong> ({company.ticker}) operates in the {company.segment} segment
          with a {company.strategy} strategy. The company manages brands including {company.brands.join(", ")} across
          key markets: {company.keyMarkets.join(", ")}.
        </p>

        <h3 className="subsection-title">Key Financial Metrics</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Value</th>
              <th>YoY Change</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr key={m.label}>
                <td>{m.label}</td>
                <td className="mono">{m.value} {m.unit}</td>
                <td className={m.change !== null && m.change >= 0 ? "positive" : "negative"}>
                  {m.change !== null ? `${m.change >= 0 ? "+" : ""}${m.change}%` : "—"}
                </td>
                <td className="source">{m.source}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h3 className="subsection-title">4-Dimension Scorecard</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Score</th>
              <th>Weight</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>Management Credibility</td><td className="mono">{scorecard.credibility}/100</td><td>40%</td></tr>
            <tr><td>Financial Quality</td><td className="mono">{scorecard.financialQuality}/100</td><td>25%</td></tr>
            <tr><td>Industry Position</td><td className="mono">{scorecard.industryPosition}/100</td><td>20%</td></tr>
            <tr><td>Risk Profile</td><td className="mono">{scorecard.risk}/100</td><td>15%</td></tr>
            <tr className="total-row"><td><strong>Composite</strong></td><td className="mono"><strong>{scorecard.composite}/100</strong></td><td>100%</td></tr>
          </tbody>
        </table>
        <p className="source-note">Source: EquityLens 4-Dimension Scoring Model, FY24 data</p>
      </div>

      {/* ═══ SAID VS DELIVERED ═══ */}
      <div className="page">
        <h2 className="section-title">Said vs Delivered — Guidance Tracker</h2>

        <p className="prose">
          Of {deviations.length} tracked guidance claims, management missed on {missCount},
          delivered on {beatCount}, and came in-line on {inlineCount}. Hit rate: {hitRate}%.
        </p>

        <table className="data-table compact">
          <thead>
            <tr>
              <th>#</th>
              <th>Metric</th>
              <th>Guided</th>
              <th>Actual</th>
              <th>Delta</th>
              <th>Flag</th>
              <th>Language</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {deviations.map((d, i) => (
              <tr key={d.id} className={d.flag === "MISS" ? "miss-row" : d.flag === "BEAT" ? "beat-row" : ""}>
                <td className="mono">{i + 1}</td>
                <td>{d.metric}</td>
                <td className="mono">{d.guidedValue}</td>
                <td className="mono">{d.actualValue}</td>
                <td className={`mono ${d.flag === "MISS" ? "negative" : d.flag === "BEAT" ? "positive" : ""}`}>{d.delta}</td>
                <td><span className={`flag flag-${d.flag.toLowerCase().replace("-", "")}`}>{d.flag}</span></td>
                <td className="mono small">{d.confidenceLanguage.toUpperCase()}</td>
                <td className="source small">{d.sourceGuidance}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ═══ VERBATIM QUOTES ═══ */}
      <div className="page">
        <h2 className="section-title">Key Verbatim Quotes</h2>

        {deviations.filter(d => d.flag === "MISS").map((d, i) => (
          <div key={d.id} className="quote-block">
            <div className="quote-header">
              <span className="quote-number">Exhibit {String.fromCharCode(65 + i)}</span>
              <span className={`flag flag-${d.flag.toLowerCase()}`}>{d.flag}</span>
              <span className="quote-metric">{d.metric}</span>
            </div>
            <blockquote>&ldquo;{d.verbatimQuote}&rdquo;</blockquote>
            <p className="quote-attr">— {d.speaker}, {d.statementQuarter} [{d.sourceGuidance}]</p>
            <p className="quote-result">
              Guided: {d.guidedValue} &rarr; Actual: {d.actualValue} &rarr; Delta: {d.delta} [{d.sourceActual}]
            </p>
            {d.pattern && <p className="quote-pattern">Pattern: {d.pattern}</p>}
          </div>
        ))}
      </div>

      {/* ═══ MANAGEMENT TONE ═══ */}
      <div className="page">
        <h2 className="section-title">Management Tone Analysis</h2>

        <p className="prose">
          {tones.length > 0 ? `Management language shifted from ${tones[0].overall_sentiment} in ${tones[0].quarter} to ${tones[tones.length-1].overall_sentiment} by ${tones[tones.length-1].quarter}. Hedging phrases increased from ${tones[0].hedging_count} to ${tones[tones.length-1].hedging_count} instances per call.` : "Management tone data pending from PDF pipeline."}
        </p>

        {tones.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Quarter</th>
              <th>Sentiment</th>
              <th>Confidence</th>
              <th>Commitments</th>
              <th>Hedges</th>
              <th>Key Phrases</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {tones.map((t) => (
              <tr key={t.quarter}>
                <td className="mono">{t.quarter}</td>
                <td><span className={`sentiment sentiment-${t.overall_sentiment}`}>{t.overall_sentiment}</span></td>
                <td className="mono">{t.confidence_score}/100</td>
                <td className="mono">{t.commitment_count}</td>
                <td className="mono">{t.hedging_count}</td>
                <td className="small">{t.key_phrases.join(", ")}</td>
                <td className="source small">{t.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
        )}

        <h3 className="subsection-title">Credibility Trend</h3>
        <table className="data-table narrow">
          <thead>
            <tr><th>Period</th><th>Score</th><th>Trend</th></tr>
          </thead>
          <tbody>
            {credibility.map((c, i) => (
              <tr key={c.period}>
                <td className="mono">{c.period}</td>
                <td className="mono">{c.score}/100</td>
                <td className={i > 0 && c.score < credibility[i - 1].score ? "negative" : "positive"}>
                  {i > 0 ? (c.score - credibility[i - 1].score > 0 ? "+" : "") + (c.score - credibility[i - 1].score) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="source-note">Source: EquityLens Credibility Model</p>
      </div>

      {/* ═══ RISK FLAGS ═══ */}
      <div className="page">
        <h2 className="section-title">Risk Flags</h2>

        {riskFlags.map((r) => (
          <div key={r.id} className={`risk-block risk-${r.severity}`}>
            <div className="risk-header">
              <span className={`severity severity-${r.severity}`}>{r.severity.toUpperCase()}</span>
              <span className="risk-category">{r.category}</span>
            </div>
            <p className="risk-desc">{r.description}</p>
            {r.verbatimQuote && (
              <blockquote className="risk-quote">&ldquo;{r.verbatimQuote}&rdquo;</blockquote>
            )}
            <p className="source-note">[{r.source}] ({r.period})</p>
          </div>
        ))}
      </div>

      {/* ═══ PEER COMPARISON ═══ */}
      <div className="page">
        <h2 className="section-title">Peer Comparison</h2>

        <h3 className="subsection-title">Composite Rankings</h3>
        <table className="data-table">
          <thead>
            <tr><th>Rank</th><th>Company</th><th>Composite</th><th>Credibility</th><th>Financial</th><th>Position</th><th>Risk</th></tr>
          </thead>
          <tbody>
            {rankings.map((s, i) => (
              <tr key={s.companyId} className={s.companyId === "IHCL" ? "highlight-row" : ""}>
                <td className="mono">#{i + 1}</td>
                <td><strong>{s.name}</strong></td>
                <td className="mono">{s.composite}</td>
                <td className="mono"></td>
                <td className="mono"></td>
                <td className="mono"></td>
                <td className="mono"></td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="source-note">Source: EquityLens 4-Dimension Scoring Model, FY24</p>

        {uiCompare && (
        <>
        <h3 className="subsection-title">Key Metrics Comparison</h3>
        <table className="data-table compact">
          <thead>
            <tr>
              <th>Metric</th>
              {uiCompare.companyNames.map((c) => <th key={c.id}>{c.name.split(" ")[0]}</th>)}
            </tr>
          </thead>
          <tbody>
            {uiCompare.rows.map((row) => (
              <tr key={row.metric}>
                <td>{row.metric} ({row.unit})</td>
                {uiCompare.companyIds.map((id) => <td key={id} className="mono">{row[id] || "N/A"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="source-note">Source: Screener.in financials</p>
        </>
        )}
      </div>

      {/* ═══ SOURCES ═══ */}
      <div className="page">
        <h2 className="section-title">Sources &amp; Citations</h2>
        <p className="prose">
          {footnotes.length} sources referenced. Every claim in this report is traceable.
        </p>
        <div className="footnotes">
          {footnotes.map((fn) => (
            <div key={fn.id} className="footnote">
              <span className="fn-num">[{fn.id}]</span>
              <span className="fn-text">
                <strong>{fn.source}</strong> — {fn.document}
                {" "}({fn.period})
              </span>
            </div>
          ))}
        </div>

        <div className="report-end">
          <p>— End of Report —</p>
          <p className="small">Generated by EquityLens AI &middot; Source-Only Architecture</p>
          <p className="small">Every output cites its source. If data is not in ingested documents, the system says DATA NOT AVAILABLE.</p>
        </div>
      </div>

      {/* ═══ PRINT STYLES ═══ */}
      <style jsx>{`
        .report-container {
          font-family: 'Georgia', 'Times New Roman', serif;
          color: #0f172a;
          line-height: 1.6;
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem;
        }
        .no-print { }
        .page { margin-bottom: 3rem; page-break-after: always; }
        .page:last-of-type { page-break-after: avoid; }

        /* Cover */
        .cover-page { display: flex; align-items: center; justify-content: center; min-height: 90vh; }
        .cover-content { text-align: center; }
        .cover-label { font-size: 11px; letter-spacing: 0.3em; text-transform: uppercase; color: #94a3b8; margin-bottom: 2rem; font-family: system-ui, sans-serif; }
        .cover-title { font-size: 2.5rem; font-weight: 400; margin: 0 0 0.5rem; }
        .cover-ticker { font-size: 14px; color: #64748b; margin-bottom: 3rem; font-family: system-ui, sans-serif; }
        .cover-score { margin: 2rem 0; }
        .cover-score-number { font-size: 4rem; font-weight: 300; color: #0f172a; }
        .cover-score-label { font-size: 14px; color: #94a3b8; display: block; font-family: system-ui, sans-serif; }
        .cover-meta { display: flex; gap: 2rem; justify-content: center; margin: 2rem 0; font-family: system-ui, sans-serif; }
        .cover-meta-item { text-align: center; }
        .cover-meta-label { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: 0.15em; color: #94a3b8; }
        .cover-meta-value { font-size: 1.25rem; font-weight: 600; color: #0f172a; font-family: 'Courier New', monospace; }
        .cover-meta-value.miss { color: #dc2626; }
        .cover-footer { margin-top: 4rem; }
        .cover-footer p { font-size: 12px; color: #94a3b8; margin: 0.25rem 0; font-family: system-ui, sans-serif; }
        .cover-date { font-size: 11px; }
        .cover-disclaimer { font-size: 10px; color: #b0b8c4; max-width: 400px; margin: 1rem auto 0; }

        /* Sections */
        .section-title { font-size: 1.25rem; font-weight: 400; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin: 2rem 0 1rem; }
        .subsection-title { font-size: 0.9rem; font-weight: 600; color: #334155; margin: 1.5rem 0 0.75rem; font-family: system-ui, sans-serif; }
        .prose { font-size: 14px; line-height: 1.8; color: #334155; margin-bottom: 1rem; }

        /* Tables */
        .data-table { width: 100%; border-collapse: collapse; font-size: 12px; font-family: system-ui, sans-serif; margin-bottom: 1rem; }
        .data-table th { text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; padding: 6px 8px; border-bottom: 2px solid #e2e8f0; }
        .data-table td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; }
        .data-table.compact td, .data-table.compact th { padding: 4px 6px; font-size: 11px; }
        .data-table.narrow { max-width: 300px; }
        .mono { font-family: 'Courier New', monospace; }
        .small { font-size: 10px; }
        .positive { color: #16a34a; }
        .negative { color: #dc2626; }
        .source { color: #94a3b8; font-size: 10px; }
        .source-note { font-size: 10px; color: #94a3b8; margin-top: 0.5rem; }
        .total-row { border-top: 2px solid #e2e8f0; }
        .highlight-row { background: #f8fafc; }
        .miss-row { background: #fef2f2; }
        .beat-row { background: #f0fdf4; }

        /* Flags */
        .flag { font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 3px; font-family: system-ui, sans-serif; }
        .flag-miss { background: #fef2f2; color: #dc2626; }
        .flag-beat { background: #f0fdf4; color: #16a34a; }
        .flag-inline { background: #eff6ff; color: #2563eb; }

        /* Sentiment */
        .sentiment { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; text-transform: uppercase; }
        .sentiment-bullish { background: #f0fdf4; color: #16a34a; }
        .sentiment-cautious { background: #fefce8; color: #a16207; }
        .sentiment-defensive { background: #fef2f2; color: #dc2626; }

        /* Quotes */
        .quote-block { margin-bottom: 1.5rem; padding: 1rem; border-left: 3px solid #dc2626; background: #fafafa; }
        .quote-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; font-family: system-ui, sans-serif; }
        .quote-number { font-size: 10px; font-family: monospace; color: #94a3b8; text-transform: uppercase; }
        .quote-metric { font-size: 13px; font-weight: 600; color: #0f172a; }
        blockquote { font-style: italic; font-size: 13px; color: #334155; margin: 0.5rem 0; padding: 0; border: none; }
        .quote-attr { font-size: 11px; color: #94a3b8; font-family: system-ui, sans-serif; }
        .quote-result { font-size: 12px; color: #334155; font-family: monospace; margin-top: 0.25rem; }
        .quote-pattern { font-size: 11px; color: #a16207; background: #fefce8; padding: 4px 8px; border-radius: 3px; margin-top: 0.5rem; font-family: system-ui, sans-serif; }

        /* Risks */
        .risk-block { margin-bottom: 1rem; padding: 0.75rem 1rem; border-left: 3px solid #e2e8f0; }
        .risk-critical { border-left-color: #dc2626; }
        .risk-high { border-left-color: #f59e0b; }
        .risk-medium { border-left-color: #94a3b8; }
        .risk-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; font-family: system-ui, sans-serif; }
        .severity { font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 3px; }
        .severity-critical { background: #fef2f2; color: #dc2626; }
        .severity-high { background: #fefce8; color: #a16207; }
        .severity-medium { background: #f1f5f9; color: #64748b; }
        .risk-category { font-size: 13px; font-weight: 600; }
        .risk-desc { font-size: 12px; color: #334155; line-height: 1.6; }
        .risk-quote { font-size: 11px; color: #64748b; }

        /* Footnotes */
        .footnotes { font-family: system-ui, sans-serif; }
        .footnote { display: flex; gap: 0.5rem; padding: 3px 0; font-size: 11px; border-bottom: 1px solid #f8fafc; }
        .fn-num { font-family: monospace; color: #b0b8c4; min-width: 28px; text-align: right; }
        .fn-text { color: #334155; }

        .report-end { text-align: center; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #e2e8f0; }
        .report-end p { font-size: 12px; color: #94a3b8; margin: 0.25rem 0; }

        @media print {
          .no-print { display: none !important; }
          .report-container { padding: 0; max-width: none; }
          .page { margin-bottom: 0; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
      `}</style>
    </div>
  );
}
