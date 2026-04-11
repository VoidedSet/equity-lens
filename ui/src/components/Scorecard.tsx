"use client";

type UIScorecard = {
  companyId: string; period: string; credibility: number;
  financialQuality: number; industryPosition: number; risk: number; composite: number;
};

type Dim = { label: string; short: string; value: number; color: string };

function CircularScore({ value, size = 120, strokeWidth = 8, color }: { value: number; size?: number; strokeWidth?: number; color: string }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="#f0f0f0"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700 ease-out"
      />
    </svg>
  );
}

export function Scorecard({ scorecard }: { scorecard: UIScorecard }) {
  const dims: Dim[] = [
    { label: "Delivery Credibility", short: "Credibility", value: scorecard.credibility, color: "#3b82f6" },
    { label: "Financial Quality", short: "Financials", value: scorecard.financialQuality, color: "#8b5cf6" },
    { label: "Industry Position", short: "Position", value: scorecard.industryPosition, color: "#06b6d4" },
    { label: "Risk Assessment", short: "Risk", value: scorecard.risk, color: "#f59e0b" },
  ];

  const grade = scorecard.composite >= 80 ? "A" : scorecard.composite >= 70 ? "B+" : scorecard.composite >= 60 ? "B" : scorecard.composite >= 50 ? "C+" : scorecard.composite >= 40 ? "C" : "D";
  const gradeColor = scorecard.composite >= 70 ? "#16a34a" : scorecard.composite >= 50 ? "#f59e0b" : "#dc2626";

  return (
    <div className="ed-section-ruled" id="scorecard">
      <div className="ed-container">
        <div className="max-w-5xl mx-auto">
          <p className="kicker mb-2">Composite Assessment</p>
          <h2 className="font-serif text-3xl lg:text-4xl text-[#222] mb-12 leading-tight">Investment Grade</h2>

          {/* Hero composite score */}
          <div className="flex items-center justify-center gap-16 mb-16 pb-12 border-b border-[#e0e0e0]">
            <div className="relative">
              <CircularScore value={scorecard.composite} size={180} strokeWidth={12} color={gradeColor} />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-serif text-6xl font-bold" style={{ color: gradeColor }}>{grade}</span>
                <span className="text-[11px] text-[#999] uppercase tracking-wider mt-1">Grade</span>
              </div>
            </div>
            <div className="max-w-sm">
              <div className="font-serif text-5xl font-bold text-[#222] mb-3">{scorecard.composite}<span className="text-2xl text-[#bbb] font-normal">/100</span></div>
              <p className="text-[15px] text-[#666] leading-relaxed">
                {scorecard.composite >= 70
                  ? "Management track record holds. Guidance credibility intact across key metrics."
                  : scorecard.composite >= 50
                  ? "Selective trust warranted. Cross-check guidance against actuals before modeling."
                  : "Credibility gaps identified. Treat forward statements with caution."}
              </p>
            </div>
          </div>

          {/* Dimension breakdown */}
          <div className="grid grid-cols-4 gap-8">
            {dims.map((dim) => (
              <div key={dim.label} className="text-center">
                <div className="relative inline-block mb-4">
                  <CircularScore value={dim.value} size={100} strokeWidth={6} color={dim.color} />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="font-serif text-2xl font-bold text-[#222]">{dim.value}</span>
                  </div>
                </div>
                <p className="text-[13px] font-semibold text-[#222] mb-1">{dim.short}</p>
                <p className="text-[10px] text-[#999] uppercase tracking-wider">{dim.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
