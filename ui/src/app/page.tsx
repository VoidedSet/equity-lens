"use client";

import { useState } from "react";
import { Bot } from "lucide-react";
import { Hero } from "@/components/Hero";
import { Sidebar } from "@/components/Sidebar";
import { CompanyHeader } from "@/components/CompanyHeader";
import { SaidVsDelivered } from "@/components/SaidVsDelivered";
import { Scorecard } from "@/components/Scorecard";
import { ManagementTone } from "@/components/ManagementTone";
import { CredibilityTrend } from "@/components/CredibilityTrend";
import { RiskFlags } from "@/components/RiskFlags";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { CompanyCompare } from "@/components/CompanyCompare";
import { NewsFeed } from "@/components/NewsFeed";
import { FootnoteSection } from "@/components/FootnoteSection";
import { SourceModal } from "@/components/SourceModal";
import { GovernanceInsights } from "@/components/GovernanceInsights";
import { FinancialGraphs } from "@/components/FinancialGraphs";
import { CompanyNarrative } from "@/components/CompanyNarrative";
import AgentChat from "@/components/AgentChat";
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
  const [isAgentOpen, setIsAgentOpen] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

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

  if (companiesLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#fafafa]">
        <p className="text-sm text-[#94a3b8]">Loading Workspace...</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#fafafa]">
      
      {/* Left Pane: Sidebar Navigation (Hidden/Hoverable but pushes content) */}
      <div 
        className={`h-full z-40 transition-all duration-300 ease-in-out flex flex-shrink-0 shadow-2xl relative ${
          isSidebarOpen ? "ml-0" : "-ml-[260px]"
        }`}
        onMouseEnter={() => setIsSidebarOpen(true)}
        onMouseLeave={() => setIsSidebarOpen(false)}
      >
        <Sidebar 
          companies={companies} 
          selectedCompany={selectedCompany} 
          onSelectCompany={setSelectedCompany} 
        />
        {/* Edge catch area to trigger hover */}
        <div className="w-2 h-full bg-[#111] border-r border-[#333] cursor-pointer relative z-50 hover:bg-[#222] transition-colors" />
      </div>

      {/* Floating Reopen Agent Button */}
      {!isAgentOpen && (
        <button
          onClick={() => setIsAgentOpen(true)}
          className="absolute top-6 right-6 z-30 px-4 py-2 bg-[#111] text-white border border-[#333] rounded shadow-lg uppercase tracking-[0.1em] text-[11px] font-semibold hover:bg-[#222] transition-colors flex items-center gap-2"
          title="Open AI Agent"
        >
          <Bot className="w-4 h-4 text-blue-400" />
          AI Desk
        </button>
      )}

      {/* Middle Pane: Main Content Workspace */}
      <div className="flex-1 overflow-y-auto scroll-smooth pl-2 relative">
        {!selectedCompany ? (
          <Hero onSelectCompany={setSelectedCompany} companies={companies} />
        ) : companyLoading ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-[#999]">Loading {selectedCompany} report...</p>
          </div>
        ) : uiCompany ? (
          <div className="p-8 max-w-5xl mx-auto space-y-10 pb-24">
            <CompanyHeader company={uiCompany} metrics={uiMetrics} />

            {/* Company Specific Narrative from Sector Analysis */}
            <CompanyNarrative companyId={selectedCompany!} />

            {/* Analyst Narrative */}
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
                <div className="bg-white border-l-4 border-[#222] p-6 shadow-sm rounded-r-lg">
                  <p className="text-[10px] uppercase tracking-widest font-semibold text-[#888] mb-3">Analyst Summary</p>
                  <p className="font-serif text-lg leading-relaxed text-[#333]">
                    {selectedCompany}&rsquo;s management guidance record is <strong>{tone}</strong>: {beats} beat{beats !== 1 ? "s" : ""}, {misses} miss{misses !== 1 ? "es" : ""}, and {inline} in-line
                    across {total} tracked forward-looking claims &mdash; a {hitPct}&thinsp;% delivery rate.
                    {score ? ` The composite credibility score stands at ${score} / 100.` : ""}
                    {risks > 0 ? ` ${risks} risk flag${risks !== 1 ? "s" : ""} identified in the source documents require attention before forming a position.` : " No material risk flags were identified in the source documents."}
                  </p>
                </div>
              );
            })()}

            {/* Financial Trends Graphs */}
            <FinancialGraphs companyId={selectedCompany} />

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
          </div>
        ) : null}
      </div>

      {/* Right Pane: Persistent AI Agent */}
      <div 
        className={`flex-shrink-0 bg-white flex flex-col h-full shadow-[-4px_0_15px_-5px_rgba(0,0,0,0.05)] z-20 transition-all duration-300 ease-in-out ${
          isAgentOpen ? "w-[450px] border-l border-[#e0e0e0]" : "w-0 border-l-0 overflow-hidden"
        }`}
      >
        <div className="w-[450px] h-full flex flex-col">
          <AgentChat onClose={() => setIsAgentOpen(false)} />
        </div>
      </div>

      <SourceModal />
    </div>
  );
}
