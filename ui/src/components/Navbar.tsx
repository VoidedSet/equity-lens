"use client";

import { useState } from "react";
import Link from "next/link";

const COMPANY_SHORT: Record<string, string> = {
  IHCL: "Indian Hotels (Taj)",
  CHALET: "Chalet Hotels",
  LEMONTREE: "Lemon Tree",
  EIH: "EIH (Oberoi)",
  JUNIPER: "Juniper (Hyatt)",
};

export function Navbar({
  selectedCompany,
  onSelectCompany,
  showNav,
  companies,
}: {
  selectedCompany: string | null;
  onSelectCompany: (id: string) => void;
  showNav: boolean;
  companies: { id: string; name: string }[];
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  if (!showNav) return null;

  const currentName = selectedCompany ? (COMPANY_SHORT[selectedCompany] || selectedCompany) : "";

  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-[#e0e0e0]">
      <div className="ed-container flex items-center justify-between h-11">
        <button
          onClick={() => onSelectCompany("")}
          className="font-serif text-[15px] font-bold text-[#222] tracking-tight cursor-pointer hover:opacity-60 transition-opacity"
        >
          EquityLens
        </button>

        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-1.5 px-3 py-1 text-[13px] font-medium text-[#222] hover:bg-[#f5f5f5] rounded transition-colors cursor-pointer"
          >
            {currentName}
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#bbb]">
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </button>

          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 z-50 bg-white border border-[#e0e0e0] rounded shadow-lg py-1 min-w-[220px]">
                {companies.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => { onSelectCompany(c.id); setDropdownOpen(false); }}
                    className={`w-full text-left px-4 py-2 text-[13px] transition-colors cursor-pointer ${
                      selectedCompany === c.id
                        ? "text-[#222] font-medium bg-[#f5f5f5]"
                        : "text-[#888] hover:text-[#222] hover:bg-[#fafafa]"
                    }`}
                  >
                    {COMPANY_SHORT[c.id] || c.name}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-4">
          <Link href="/board" className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#888] hover:text-[#222] transition-colors">
            Evidence Board
          </Link>
          <Link href="/report" className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#bbb] hover:text-[#222] transition-colors">
            Export
          </Link>
        </div>
      </div>
    </nav>
  );
}
