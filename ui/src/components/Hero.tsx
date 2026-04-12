"use client";

import { SectorAnalysis } from "@/components/SectorAnalysis";

const COMPANIES: Record<string, { short: string; tagline: string }> = {
  IHCL: { short: "Indian Hotels (Taj)", tagline: "Premium & luxury hybrid" },
  CHALET: { short: "Chalet Hotels", tagline: "Asset-heavy upper midscale" },
  LEMONTREE: { short: "Lemon Tree Hotels", tagline: "Economy & midscale disruptor" },
  EIH: { short: "EIH (Oberoi)", tagline: "Ultra-luxury, selective growth" },
  JUNIPER: { short: "Juniper (Hyatt)", tagline: "New entrant, brand-powered" },
};

export function Hero({ onSelectCompany, companies }: { onSelectCompany: (id: string) => void; companies: { id: string; name: string }[] }) {
  const today = new Date();
  const issue = `Vol. 1 — ${today.toLocaleDateString("en-IN", { month: "long", year: "numeric" })}`;

  return (
    <div style={{ padding: "4rem 0" }}>
      <div className="ed-container">
        {/* Masthead line */}
        <div className="flex items-center justify-between pb-4 mb-12 border-b-2 border-[#222]">
          <span className="text-[11px] tracking-[0.3em] uppercase font-medium text-[#888]">{issue}</span>
          <span className="text-[11px] tracking-[0.2em] uppercase font-medium text-[#888]">Indian Hospitality Sector</span>
        </div>

        {/* Title */}
        <h1 className="font-serif text-7xl sm:text-8xl lg:text-[7.5rem] font-bold leading-[0.9] tracking-tight mb-6 text-[#222]">
          Equity Lens
        </h1>
        <hr className="section-rule-thick w-20 mb-8" />
        <p className="font-serif text-2xl sm:text-3xl leading-snug mb-4 text-[#222] max-w-xl">
          Did management keep their promises?
        </p>
        <p className="text-[15px] max-w-md leading-[1.85] text-[#888] mb-16">
          Every forward-looking claim extracted from earnings calls, matched against actual results, cited to the source. No opinions. Just evidence.
        </p>

        {/* Company grid — table of contents */}
        <div className="border-t-2 border-[#222]">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
            {companies.map((c, i) => {
              const info = COMPANIES[c.id] || { short: c.name, tagline: "" };
              return (
                <button
                  key={c.id}
                  onClick={() => onSelectCompany(c.id)}
                  className="text-left py-5 pr-5 border-b lg:border-b-0 lg:border-r border-[#e0e0e0] last:border-r-0 hover:bg-[#f9f9f9] transition-colors cursor-pointer group"
                >
                  <span className="text-[10px] font-mono text-[#bbb] block mb-1">0{i + 1}</span>
                  <span className="font-serif text-[17px] font-semibold block mb-1 text-[#222] group-hover:underline underline-offset-4 decoration-1">
                    {info.short}
                  </span>
                  <span className="text-[12px] text-[#999]">{info.tagline}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Footer line */}
        <div className="mt-12 pt-4 border-t border-[#e0e0e0] flex items-center justify-between text-[10px] text-[#bbb] tracking-wider uppercase">
          <span>Groq Llama 3.3 70B &bull; Neo4j &bull; Supabase &bull; RAG Pipeline</span>
          <span>Zero hallucination</span>
        </div>
        
        {/* Sector Analysis Part 1 & 3 */}
        <SectorAnalysis />
      </div>
    </div>
  );
}
