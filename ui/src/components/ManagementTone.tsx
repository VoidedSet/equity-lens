"use client";

type ToneItem = {
  quarter: string; overall_sentiment: string; confidence_score: number;
  key_phrases: string[]; hedging_count: number; commitment_count: number; source: string;
};

const sentimentColors: Record<string, { bg: string; text: string; label: string }> = {
  bullish: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Bullish" },
  cautious: { bg: "bg-amber-50", text: "text-amber-700", label: "Cautious" },
  defensive: { bg: "bg-red-50", text: "text-red-700", label: "Defensive" },
  neutral: { bg: "bg-slate-50", text: "text-slate-600", label: "Neutral" },
};

export function ManagementTone({ tones }: { tones: ToneItem[] }) {

  if (!tones.length) return null;

  // Calculate the shift
  const firstConf = tones[0].confidence_score;
  const lastConf = tones[tones.length - 1].confidence_score;
  const confDelta = lastConf - firstConf;

  const firstHedge = tones[0].hedging_count;
  const lastHedge = tones[tones.length - 1].hedging_count;

  return (
    <div className="ed-section-ruled" id="tone">
      <div className="ed-container">
        <p className="kicker mb-2">Tone Analysis</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] mb-6 leading-tight">Management Language Shift</h2>

        {/* Trend summary */}
        <div className="max-w-3xl mx-auto mb-12">
          <div className="grid grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-1">Sentiment Shift</p>
              <p className="text-[15px] text-[#333]">
                <span className="font-semibold text-emerald-600">{tones[0].overall_sentiment}</span>
                {" → "}
                <span className="font-semibold text-red-600">{tones[tones.length - 1].overall_sentiment}</span>
              </p>
            </div>
            <div>
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-1">Confidence</p>
              <p className="text-[15px] text-[#333]">
                <span className={confDelta < 0 ? "text-red-600 font-semibold" : "text-[#333]"}>
                  {confDelta > 0 ? "+" : ""}{confDelta} pts
                </span>
              </p>
            </div>
            <div>
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-1">Hedging</p>
              <p className="text-[15px] text-[#333]">
                <span className="font-semibold">{firstHedge}</span>
                {" → "}
                <span className={lastHedge > firstHedge ? "text-amber-600 font-semibold" : "text-[#333]"}>{lastHedge}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Quarter breakdown */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-0 border-t border-[#e0e0e0]">
          {tones.map((t) => {
            const s = sentimentColors[t.overall_sentiment] || sentimentColors.neutral;
            const hedgeRatio = t.hedging_count / (t.hedging_count + t.commitment_count);

            return (
              <div key={t.quarter} className="border-r border-[#e0e0e0] last:border-r-0 p-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-serif text-lg font-bold text-[#222]">{t.quarter}</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#888]">{s.label}</span>
                </div>

                <div className="font-serif text-3xl font-bold text-[#222] mb-1">{t.confidence_score}</div>
                <p className="text-[10px] text-[#999] uppercase tracking-wider mb-3">Confidence</p>

                <div className="h-1 bg-[#eee] rounded-full overflow-hidden mb-3">
                  <div className="h-full flex rounded-full overflow-hidden">
                    <div className="h-full bg-green-500" style={{ width: `${(1 - hedgeRatio) * t.confidence_score}%` }} />
                    <div className="h-full bg-red-400" style={{ width: `${hedgeRatio * t.confidence_score}%` }} />
                  </div>
                </div>

                <div className="flex justify-between text-[11px] text-[#888] mb-3">
                  <span>{t.commitment_count} commits</span>
                  <span>{t.hedging_count} hedges</span>
                </div>

                <div className="flex flex-wrap gap-1">
                  {t.key_phrases.slice(0, 3).map((phrase) => (
                    <span key={phrase} className="text-[10px] font-mono text-[#888] italic">&ldquo;{phrase}&rdquo;</span>
                  ))}
                </div>

                <button
                  onClick={() => {
                    window.dispatchEvent(new CustomEvent("open-source", { detail: { ref: t.source, company: "IHCL", quote: "" } }));
                  }}
                  className="mt-3 text-[10px] text-[#bbb] hover:text-[#222] cursor-pointer transition-colors"
                >
                  Source: {t.source}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
