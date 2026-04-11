"use client";

export function Footer() {
  return (
    <footer className="ed-container py-16">
      <div className="border-t border-[#e0e0e0] pt-8">
        <p className="text-[11px] tracking-[0.15em] uppercase text-[#bbb] font-medium mb-3">
          EquityLens AI
        </p>
        <p className="text-xs text-[#999] leading-relaxed max-w-md">
          Every output cites its source. If data is not in ingested documents,
          the system says DATA NOT AVAILABLE. Built on 3-Layer Source-Only
          Architecture, Gemma 3 27B-IT, and Supabase.
        </p>
        <p className="text-[10px] text-[#ccc] mt-4">
          DataHack 2026 &middot; Hotel Sector Intelligence
        </p>
      </div>
    </footer>
  );
}
