"use client";

import { companies } from "@/lib/data";

export function Hero({ onSelectCompany }: { onSelectCompany: (id: string) => void }) {
  return (
    <section className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="max-w-2xl mx-auto text-center">
        {/* Masthead — like a publication */}
        <p className="text-[11px] tracking-[0.35em] uppercase text-[#94a3b8] mb-12 font-medium">
          EquityLens AI &mdash; Hotel Sector Intelligence
        </p>

        <h1 className="text-4xl sm:text-5xl font-serif font-normal text-[#0f172a] leading-tight mb-8">
          Did management keep<br />their promises?
        </h1>

        <p className="text-base text-[#64748b] max-w-lg mx-auto mb-16 leading-relaxed">
          We extract every forward-looking claim from earnings calls, match it
          against actual results, and cite every source. No opinions. No
          predictions. Just evidence.
        </p>

        {/* Company pills — minimal */}
        <div className="space-y-3">
          <p className="text-[11px] tracking-[0.2em] uppercase text-[#b0b8c4]">Read the report for</p>
          <div className="flex flex-wrap justify-center gap-2">
            {companies.map((c) => {
              const label =
                c.id === "IHCL" ? "IHCL (Taj)" :
                c.id === "CHALET" ? "Chalet Hotels" :
                c.id === "LEMONTREE" ? "Lemon Tree" :
                c.id === "EIH" ? "EIH (Oberoi)" : "ITC Hotels";
              return (
                <button
                  key={c.id}
                  onClick={() => onSelectCompany(c.id)}
                  className="px-4 py-2 text-sm font-medium text-[#334155] border border-[#e2e8f0] rounded-full hover:bg-[#0f172a] hover:text-white hover:border-[#0f172a] transition-all duration-200 cursor-pointer"
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
