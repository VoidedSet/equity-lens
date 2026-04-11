"use client";

type UIScorecard = {
  companyId: string; period: string; credibility: number;
  financialQuality: number; industryPosition: number; risk: number; composite: number;
};

type Dim = { label: string; value: number; weight: number };

export function Scorecard({ scorecard }: { scorecard: UIScorecard }) {
  const dims: Dim[] = [
    { label: "Credibility", value: scorecard.credibility, weight: 30 },
    { label: "Financial Quality", value: scorecard.financialQuality, weight: 25 },
    { label: "Industry Position", value: scorecard.industryPosition, weight: 25 },
    { label: "Risk Assessment", value: scorecard.risk, weight: 20 },
  ];

  return (
    <div className="ed-section-ruled" id="scorecard">
      <div className="ed-container">
        <p className="kicker mb-2">Assessment</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] mb-8 leading-tight">Company Scorecard</h2>

        <div className="ed-grid">
          <div>
            <div className="flex items-end gap-6 mb-8">
              <div className="stat-big">{scorecard.composite}</div>
              <p className="text-[14px] text-[#888] leading-relaxed pb-1">
                {scorecard.composite >= 70
                  ? "Strong overall — guidance credibility intact."
                  : scorecard.composite >= 50
                  ? "Mixed signals — selective trust warranted."
                  : "Weak — significant credibility gaps identified."}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-x-6 gap-y-5">
              {dims.map((dim) => (
                <div key={dim.label} className="border-t border-[#e0e0e0] pt-3">
                  <div className="flex items-baseline justify-between mb-1">
                    <p className="text-[13px] font-semibold text-[#222]">{dim.label}</p>
                    <span className="font-serif text-xl font-bold text-[#222]">{dim.value}</span>
                  </div>
                  <p className="text-[10px] text-[#999] mb-2">Weight: {dim.weight}%</p>
                  <div className="h-1 bg-[#eee] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${dim.value}%`,
                        background: dim.value >= 70 ? "#16a34a" : dim.value >= 50 ? "#ca8a04" : "#dc2626",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <aside>
            <div className="sidebar-card">
              <p className="kicker mb-3">Composite</p>
              <div className="stat-big">{scorecard.composite}<span className="text-lg font-normal text-[#999]">/100</span></div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
