"use client";

type CredPoint = { period: string; score: number };
type OpmPoint = { period: string; opm: number };

export function CredibilityTrend({ credibilityTrend, opmTrend }: { credibilityTrend: CredPoint[]; opmTrend: OpmPoint[] }) {
  const first = credibilityTrend[0];
  const last = credibilityTrend[credibilityTrend.length - 1];
  const delta = last ? last.score - first.score : 0;

  return (
    <div className="ed-section-ruled" id="trends">
      <div className="ed-container">
        <p className="kicker mb-2">Patterns</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] mb-6 leading-tight">Credibility &amp; Margin Trends</h2>

        <div className="ed-grid">
          <div>
            <p className="text-[15px] text-[#333] leading-[1.9] mb-8">
              Management&apos;s guidance accuracy has eroded steadily. The credibility
              score fell from <span className="highlight">{first?.score ?? "—"}</span> in {first?.period ?? "—"} to{" "}
              <span className="highlight-red">{last?.score ?? "—"}</span> in {last?.period ?? "—"} — a{" "}
              <span className="highlight-red">{Math.abs(delta)}-point decline</span> driven by
              repeated over-guidance on RevPAR and room additions.
            </p>

            {/* Credibility inline table */}
            <div className="border-t-2 border-[#222] mb-10">
              <div className="grid grid-cols-4">
                {credibilityTrend.map((r, i) => (
                  <div key={r.period} className="border-r border-[#e0e0e0] last:border-r-0 py-4 pr-4">
                    <p className="text-[10px] text-[#999] uppercase tracking-wider mb-1">{r.period}</p>
                    <p className={`font-serif text-2xl font-bold ${i === credibilityTrend.length - 1 ? "text-red-600" : "text-[#222]"}`}>{r.score}</p>
                  </div>
                ))}
              </div>
            </div>

            {opmTrend.length > 0 && (
              <>
                <h3 className="font-serif text-xl text-[#222] mb-3">Operating Margin Trend</h3>
                <p className="text-[14px] text-[#888] leading-[1.85] mb-4">
                  Watch for margin compression from mix shifts or cost inflation.
                </p>
                <div className="border-t border-[#e0e0e0]">
                  <div className="grid grid-cols-4">
                    {opmTrend.slice(-4).map((r) => (
                      <div key={r.period} className="border-r border-[#e0e0e0] last:border-r-0 py-4 pr-4">
                        <p className="text-[10px] text-[#999] uppercase tracking-wider mb-1">{r.period}</p>
                        <p className="font-serif text-2xl font-bold text-[#222]">{r.opm}%</p>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          <aside>
            <div className="sidebar-card" style={{ position: "sticky", top: "4rem" }}>
              <p className="kicker mb-3">Credibility Delta</p>
              <div className="stat-big text-red-600">{delta > 0 ? "+" : ""}{delta}</div>
              <p className="stat-label">Point Change</p>
              <hr className="my-4 border-[#e0e0e0]" />
              <p className="text-[13px] text-[#888] leading-relaxed italic">
                &ldquo;When credibility declines quarter-over-quarter, future guidance should be discounted accordingly.&rdquo;
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
