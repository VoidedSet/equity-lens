"use client";

import { companies } from "@/lib/data";

export function Navbar({
  selectedCompany,
  onSelectCompany,
  showNav,
}: {
  selectedCompany: string | null;
  onSelectCompany: (id: string) => void;
  showNav: boolean;
}) {
  if (!showNav) return null;

  return (
    <nav className="sticky top-0 z-50 bg-[#fafafa]/90 backdrop-blur-md border-b border-[#e2e8f0]">
      <div className="max-w-2xl mx-auto px-6 flex items-center justify-between h-12">
        <span className="text-[11px] tracking-[0.2em] uppercase text-[#94a3b8] font-medium">
          EquityLens AI
        </span>

        {/* Company switcher */}
        <div className="flex items-center gap-1">
          {companies.map((c) => (
            <button
              key={c.id}
              onClick={() => onSelectCompany(c.id)}
              className={`px-2.5 py-1 text-xs font-medium transition-all cursor-pointer rounded ${
                selectedCompany === c.id
                  ? "text-[#0f172a] bg-white border border-[#e2e8f0]"
                  : "text-[#b0b8c4] hover:text-[#64748b]"
              }`}
            >
              {c.id}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}
