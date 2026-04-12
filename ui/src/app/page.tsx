"use client";

import { useState } from "react";
import { Hero } from "@/components/Hero";
import { Navbar } from "@/components/Navbar";
import { CompanyHeader } from "@/components/CompanyHeader";
import { SaidVsDelivered } from "@/components/SaidVsDelivered";
import { Scorecard } from "@/components/Scorecard";
import { ManagementTone } from "@/components/ManagementTone";
import { CredibilityTrend } from "@/components/CredibilityTrend";
import { RiskFlags } from "@/components/RiskFlags";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { CompanyCompare } from "@/components/CompanyCompare";
import { AskSection } from "@/components/AskSection";
import { NewsFeed } from "@/components/NewsFeed";
import { FootnoteSection } from "@/components/FootnoteSection";
import { Footer } from "@/components/Footer";
import { SourceModal } from "@/components/SourceModal";
import { GovernanceInsights } from "@/components/GovernanceInsights";
import { useCompanies, useCompanyData, useCompare, useNews } from "@/lib/hooks";
import {
  toUICompany,
  toUIKeyMetrics,
  toUIDeviations,
  toUIScorecard,
  toUIRiskFlags,
  toUICredibility,
  toUICompareTable,
} from "@/lib/transforms";

export default function Home() {
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);

  // Fetch companies list
  const { companies, loading: companiesLoading } = useCompanies();

  // Fetch selected company data
  const { data: companyData, loading: companyLoading } = useCompanyData(selectedCompany);

  // Fetch comparison data
  const { data: compareData } = useCompare();

  // Fetch news
  const { data: newsData } = useNews(selectedCompany);

  // Transform API data into component shapes
  const uiCompany = companyData ? toUICompany(companyData.company) : null;
  const uiMetrics = companyData ? toUIKeyMetrics(companyData.keyMetrics) : [];
  const uiDeviations = companyData ? toUIDeviations(companyData.deviations, companyData.guidance) : [];
  const uiScorecard = companyData?.scorecards?.[0] ? toUIScorecard(companyData.scorecards[0]) : null;
  const uiRiskFlags = companyData ? toUIRiskFlags(companyData.riskFlags) : [];
  const uiCredibility = companyData ? toUICredibility(companyData.credibility) : [];
  const uiCompare = compareData ? toUICompareTable(compareData) : null;

  // Build OPM trend from financials
  const opmTrend = companyData
    ? companyData.quarterly
        .filter((q) => q.metric === "opm")
        .sort((a, b) => a.period.localeCompare(b.period))
        .slice(-6)
        .map((q) => ({ period: q.period, opm: q.value }))
    : [];

  // Build footnotes from sources in deviations + risk flags
  const footnotes = companyData
    ? [
        ...companyData.deviations.map((d, i) => ({
          id: i + 1,
          source: d.source_guidance.split(" | ")[0] || d.source_guidance,
          document: d.source_guidance,
          period: d.period,
        })),
        ...companyData.riskFlags.map((r, i) => ({
          id: companyData.deviations.length + i + 1,
          source: r.source_document.split(" | ")[0] || r.source_document,
          document: r.source_document,
          period: r.period,
        })),
      ]
    : [];

  // Graph nodes need type cast for component
  const graphNodes = companyData?.graph?.nodes?.map((n) => ({
    ...n,
    type: n.type as "company" | "city" | "segment" | "theme" | "warning" | "strategy",
  })) || [];
  const graphEdges = companyData?.graph?.edges || [];

  if (companiesLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-sm text-[#94a3b8]">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar
        selectedCompany={selectedCompany}
        onSelectCompany={setSelectedCompany}
        showNav={!!selectedCompany}
        companies={companies}
      />

      {!selectedCompany ? (
        <Hero onSelectCompany={setSelectedCompany} companies={companies} />
      ) : companyLoading ? (
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-sm text-[#999]">Loading {selectedCompany} report...</p>
        </div>
      ) : uiCompany ? (
        <>
          <CompanyHeader company={uiCompany} metrics={uiMetrics} />

          {/* ── Editorial narrative lede ── */}
          {uiDeviations.length > 0 && (() => {
            const beats  = uiDeviations.filter((d) => d.flag === "BEAT").length;
            const misses = uiDeviations.filter((d) => d.flag === "MISS").length;
            const inline = uiDeviations.filter((d) => d.flag === "IN-LINE").length;
            const total  = uiDeviations.length;
            const hitPct = Math.round(((beats + inline) / total) * 100);
            const tone   = hitPct >= 70 ? "credible" : hitPct >= 50 ? "uneven" : "poor";
            const score  = uiScorecard?.composite;
            const risks  = uiRiskFlags.length;
            return (
              <div className="ed-section-ruled">
                <div className="ed-container">
                  <p className="kicker mb-3">Analyst Summary &mdash; {selectedCompany}</p>
                  <p className="font-serif text-[1.15rem] leading-[1.95] text-[#333] max-w-3xl drop-cap">
                    {selectedCompany}&rsquo;s management guidance record is <strong>{tone}</strong>: {beats} beat{beats !== 1 ? "s" : ""}, {misses} miss{misses !== 1 ? "es" : ""}, and {inline} in-line
                    across {total} tracked forward-looking claims &mdash; a {hitPct}&thinsp;% delivery rate.
                    {score ? ` The composite credibility score stands at ${score} / 100.` : ""}
                    {risks > 0 ? ` ${risks} risk flag${risks !== 1 ? "s" : ""} identified in the source documents require attention before forming a position.` : " No material risk flags were identified in the source documents."}
                  </p>
                </div>
              </div>
            );
          })()}

          {uiDeviations.length > 0 && <SaidVsDelivered deviations={uiDeviations} />}
          {companyData?.managementTone && companyData.managementTone.length > 0 && (
            <ManagementTone tones={companyData.managementTone} />
          )}
          {uiScorecard && <Scorecard scorecard={uiScorecard} />}
          {(uiCredibility.length > 0 || opmTrend.length > 0) && (
            <CredibilityTrend credibilityTrend={uiCredibility} opmTrend={opmTrend} />
          )}
          {uiRiskFlags.length > 0 && <RiskFlags risks={uiRiskFlags} />}
          <GovernanceInsights companyId={selectedCompany || undefined} />
          <KnowledgeGraph companyCode={selectedCompany || undefined} />
          {uiCompare && (
            <CompanyCompare
              rankings={uiCompare.rankings}
              rows={uiCompare.rows}
              companyIds={uiCompare.companyIds}
              companyNames={uiCompare.companyNames}
            />
          )}
          {newsData && newsData.items.length > 0 && (
            <NewsFeed items={newsData.items} digestDate={newsData.digest_date || ""} />
          )}
          {footnotes.length > 0 && <FootnoteSection footnotes={footnotes} />}
          <AskSection />
        </>
      ) : null}

      <SourceModal />
    </div>
  );
}
