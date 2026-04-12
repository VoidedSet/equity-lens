"use client";

import Link from "next/link";
import { BrainCircuit, FileText, Database, Layers, LayoutDashboard } from "lucide-react";

const COMPANY_SHORT: Record<string, string> = {
  IHCL: "Indian Hotels (Taj)",
  CHALET: "Chalet Hotels",
  LEMONTREE: "Lemon Tree",
  EIH: "EIH (Oberoi)",
  JUNIPER: "Juniper (Hyatt)",
};

export function Sidebar({
  selectedCompany,
  onSelectCompany,
  companies,
}: {
  selectedCompany: string | null;
  onSelectCompany: (id: string) => void;
  companies: { id: string; name: string }[];
}) {
  return (
    <aside className="w-[260px] flex-shrink-0 bg-[#111] text-white flex flex-col h-full border-r border-[#333]">
      <div className="p-6 border-b border-[#333]">
        <h1 className="font-serif text-[18px] font-bold tracking-tight text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-blue-400" />
          EquityLens
        </h1>
        <p className="text-[11px] text-[#888] mt-1 font-mono uppercase tracking-widest">
          Analyst Terminal
        </p>
      </div>

      <div className="flex-1 overflow-y-auto py-6 flex flex-col gap-8">
        <div className="px-6">
           <h2 className="text-[10px] font-semibold text-[#666] uppercase tracking-[0.15em] mb-4">Workspace</h2>
           <button 
             onClick={() => onSelectCompany("")}
             className={`flex items-center gap-3 w-full text-left text-[13px] transition-colors ${!selectedCompany ? 'text-white' : 'text-[#888] hover:text-[#ccc]'}`}
           >
              <LayoutDashboard className="w-4 h-4" />
              Overview Home
           </button>
        </div>

        <div className="px-6">
          <h2 className="text-[10px] font-semibold text-[#666] uppercase tracking-[0.15em] mb-4">Coverage Universe</h2>
          <div className="flex flex-col gap-2">
            {companies.map((c) => {
              const isSelected = selectedCompany === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => onSelectCompany(c.id)}
                  className={`flex items-center gap-3 w-full text-left px-3 py-2 rounded-lg text-[13px] transition-all ${
                    isSelected
                      ? "bg-[#222] text-white font-medium border border-[#444]"
                      : "text-[#888] hover:bg-[#1a1a1a] hover:text-[#ccc] border border-transparent"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${isSelected ? "bg-blue-500" : "bg-[#444]"}`} />
                  {COMPANY_SHORT[c.id] || c.name}
                </button>
              );
            })}
          </div>
        </div>

        <div className="px-6 mt-auto">
          <h2 className="text-[10px] font-semibold text-[#666] uppercase tracking-[0.15em] mb-4">Tools</h2>
          <div className="flex flex-col gap-3">
             <Link href="/board" className="flex items-center gap-3 w-full text-left text-[13px] text-[#888] hover:text-[#ccc] transition-colors">
               <Database className="w-4 h-4" />
               Evidence Board
             </Link>
             <Link href="/report" className="flex items-center gap-3 w-full text-left text-[13px] text-[#888] hover:text-[#ccc] transition-colors">
               <FileText className="w-4 h-4" />
               Export Report
             </Link>
          </div>
        </div>
      </div>
      
      <div className="p-6 border-t border-[#333] bg-[#0a0a0a]">
        <div className="flex items-center gap-3">
           <div className="w-8 h-8 rounded-full bg-[#333] flex items-center justify-center text-[10px] font-bold">
              EA
           </div>
           <div>
             <p className="text-[12px] font-medium text-white">Equity Analyst</p>
             <p className="text-[10px] text-[#666]">Terminal Version 1.0</p>
           </div>
        </div>
      </div>
    </aside>
  );
}
