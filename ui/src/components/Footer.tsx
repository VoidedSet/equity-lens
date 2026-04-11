"use client";

export function Footer() {
  return (
    <footer className="max-w-2xl mx-auto px-6 py-16">
      <div className="border-t border-[#e2e8f0] pt-8">
        <p className="text-[11px] tracking-[0.2em] uppercase text-[#b0b8c4] font-medium mb-3">
          EquityLens AI
        </p>
        <p className="text-xs text-[#94a3b8] leading-relaxed max-w-md">
          Every output cites its source. If data is not in ingested documents,
          the system says DATA NOT AVAILABLE. Built on 3-Layer Source-Only
          Architecture, Gemma 3 27B-IT, and Supabase.
        </p>
        <p className="text-[10px] text-[#cbd5e1] mt-4">
          DataHack 2026 &middot; Hotel Sector Intelligence
        </p>
      </div>
    </footer>
  );
}
