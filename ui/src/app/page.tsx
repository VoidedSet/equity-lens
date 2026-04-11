"use client";

import { useState } from "react";
import { Hero } from "@/components/Hero";
import { Navbar } from "@/components/Navbar";
import { CompanyHeader } from "@/components/CompanyHeader";
import { SaidVsDelivered } from "@/components/SaidVsDelivered";
import { Scorecard } from "@/components/Scorecard";
import { CredibilityTrend } from "@/components/CredibilityTrend";
import { RiskFlags } from "@/components/RiskFlags";
import { CompanyCompare } from "@/components/CompanyCompare";
import { AskSection } from "@/components/AskSection";
import { Footer } from "@/components/Footer";
import {
  companies,
  ihclKeyMetrics,
  ihclDeviations,
  ihclScorecard,
  ihclRiskFlags,
} from "@/lib/data";

export default function Home() {
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);

  const company = companies.find((c) => c.id === selectedCompany);

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar
        selectedCompany={selectedCompany}
        onSelectCompany={setSelectedCompany}
        showNav={!!selectedCompany}
      />

      {!selectedCompany ? (
        <Hero onSelectCompany={setSelectedCompany} />
      ) : (
        <>
          {company && (
            <article>
              <CompanyHeader company={company} metrics={ihclKeyMetrics} />
              <SaidVsDelivered deviations={ihclDeviations} />
              <Scorecard scorecard={ihclScorecard} />
              <CredibilityTrend />
              <RiskFlags risks={ihclRiskFlags} />
              <CompanyCompare />
              <AskSection />
            </article>
          )}
        </>
      )}

      <Footer />
    </div>
  );
}
