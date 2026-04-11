"use client";

type Footnote = { id: number; source: string; document: string; page?: string; timestamp?: string; period: string };

export function FootnoteSection({ footnotes }: { footnotes: Footnote[] }) {
  return (
    <div className="ed-section-ruled" id="sources">
      <div className="ed-container">
        <div className="flex items-end justify-between mb-6">
          <div>
            <p className="kicker mb-2">Sources &amp; Citations</p>
            <h2 className="font-serif text-3xl lg:text-4xl text-[#222] leading-tight">Appendix</h2>
          </div>
          <div className="text-right">
            <span className="font-serif text-3xl font-bold text-[#222]">{footnotes.length}</span>
            <p className="text-[10px] uppercase tracking-[0.15em] text-[#999] mt-1">Sources</p>
          </div>
        </div>

        <p className="text-[14px] leading-[1.85] mb-6 max-w-3xl text-[#888]">
          Every claim in this report is traceable to a specific document, page, and
          time period. If a claim cannot be cited, it is not made.
        </p>

        <div className="border-t border-[#e0e0e0]">
          {footnotes.map((fn) => (
            <div key={fn.id} className="flex gap-3 py-2.5 border-b border-[#eee]">
              <span className="text-[11px] font-mono w-6 shrink-0 text-right text-[#bbb]">[{fn.id}]</span>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent("open-source", { detail: { ref: fn.document, company: "IHCL", quote: "" } }));
                }}
                className="text-[13px] text-[#888] leading-relaxed hover:text-[#222] transition-colors cursor-pointer group text-left"
              >
                <span className="font-medium text-[#222] group-hover:underline">{fn.source}</span>
                <span className="text-[#bbb]"> — </span>
                <span className="font-mono text-[12px] text-[#888]">{fn.document}</span>
                {fn.page && <span className="text-[#bbb]">, p. {fn.page}</span>}
                {fn.timestamp && <span className="text-[#bbb]">, @{fn.timestamp}</span>}
                <span className="text-[#ccc]"> ({fn.period})</span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
