"use client";

import { useEffect, useState, useMemo } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

type CSVRow = Record<string, string>;

export function FinancialGraphs({ companyId }: { companyId: string }) {
  const [activeTab, setActiveTab] = useState<"pl" | "margins" | "returns" | "balance">("pl");
  const [plData, setPlData] = useState<any[]>([]);
  const [crossData, setCrossData] = useState<any[]>([]);
  const [bsData, setBsData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);

    const loadCSV = async (fileName: string) => {
      try {
        const res = await fetch(`/api/data/csv?companyId=${companyId}&fileName=${fileName}`);
        if (!res.ok) return [];
        const { data } = await res.json();
        return data; // Array of { Metric: "...", "Mar 2014": "...", ... }
      } catch {
        return [];
      }
    };

    Promise.all([
      loadCSV("profit_loss_enriched.csv"),
      loadCSV("cross_metrics.csv"),
      loadCSV("balance_sheet_enriched.csv"),
    ]).then(([plRaw, crossRaw, bsRaw]) => {
      setPlData(transposeData(plRaw));
      setCrossData(transposeData(crossRaw));
      setBsData(transposeData(bsRaw));
      setLoading(false);
    });
  }, [companyId]);

  // Transpose from [{Metric: "Sales", "Mar 2014": "100"}, ...] to [{period: "Mar 2014", Sales: 100}, ...]
  function transposeData(rows: CSVRow[]) {
    if (!rows || rows.length === 0) return [];
    const periods = Object.keys(rows[0]).filter(k => k !== "Metric" && k !== "TTM");
    return periods.map(period => {
      const point: any = { period };
      rows.forEach(row => {
        const metricName = row["Metric"]?.replace(/[\+\%]/g, "").trim();
        if (metricName) {
          const val = parseFloat(row[period]?.replace(/,/g, "") || "NaN");
          if (!isNaN(val)) point[metricName] = val;
        }
      });
      return point;
    });
  }

  if (loading) {
    return <div className="h-64 flex items-center justify-center text-[#999] text-sm">Loading charts...</div>;
  }

  const tabs = [
    { id: "pl", label: "Revenue & Profit" },
    { id: "margins", label: "Profit Margins" },
    { id: "returns", label: "Returns (ROE/ROCE)" },
    { id: "balance", label: "Balance Sheet Health" },
  ] as const;

  return (
    <div className="bg-white border border-[#e0e0e0] rounded-xl shadow-sm overflow-hidden mb-8">
      <div className="px-5 py-4 border-b border-[#e0e0e0] flex justify-between items-center bg-[#fafafa]">
        <h3 className="font-serif text-lg font-medium text-[#222]">Financial Trends</h3>
        <div className="flex gap-2">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-wider rounded transition-colors ${
                activeTab === t.id ? "bg-[#222] text-white" : "text-[#777] hover:bg-[#eaeaea]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5">
        {activeTab === "pl" && (
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={plData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                <XAxis dataKey="period" tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} />
                <YAxis yAxisId="left" tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} tickFormatter={(v) => `₹${v}`} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '13px', paddingTop: '10px' }} />
                <Bar yAxisId="left" dataKey="Sales" name="Total Revenue" fill="#1e3a5f" radius={[4, 4, 0, 0]} />
                <Bar yAxisId="left" dataKey="Net Profit" name="Net Profit" fill="#2d8544" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {activeTab === "margins" && (
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={plData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                <XAxis dataKey="period" tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} />
                <YAxis tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} tickFormatter={(v) => `${v}%`} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '13px', paddingTop: '10px' }} />
                <Line type="monotone" dataKey="OPM" name="Operating Margin (%)" stroke="#6b4c9a" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="Net Profit Margin" name="Net Margin (%)" stroke="#1a6b6b" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {activeTab === "returns" && (
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={crossData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                <XAxis dataKey="period" tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} />
                <YAxis tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} tickFormatter={(v) => `${v}%`} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '13px', paddingTop: '10px' }} />
                <Line type="monotone" dataKey="ROE" name="Return on Equity" stroke="#8b6914" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="ROCE" name="Return on Capital Employed" stroke="#1e3a5f" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {activeTab === "balance" && (
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bsData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                <XAxis dataKey="period" tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} />
                <YAxis tick={{fontSize: 12, fill: "#888"}} axisLine={{stroke: "#ddd"}} tickLine={false} tickFormatter={(v) => `₹${v}`} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #ddd', fontSize: '13px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '13px', paddingTop: '10px' }} />
                <Bar dataKey="Total Assets" name="Total Assets" fill="#bbb" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Total Liabilities" name="Total Liabilities" fill="#cf6679" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Equity Capital" name="Equity" fill="#1e3a5f" radius={[4, 4, 0, 0]} stackId="a" />
                <Bar dataKey="Reserves" name="Reserves" fill="#4b72a8" radius={[4, 4, 0, 0]} stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
