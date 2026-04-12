"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

type SourceInfo = {
  type: "pdf" | "csv";
  relativePath: string;
  page: number | null;
  label: string;
  pdfUrl: string | null;
  csvUrl: string | null;
};

type TranscriptEntry = { speaker?: string; text?: string; timestamp?: string; [key: string]: unknown };

function JSONTranscriptViewer({ url, searchQuote }: { url: string; searchQuote: string }) {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Normalize generic filler words for matching
  const stopWords = new Set(["the","a","an","and","or","but","in","on","at","to","for","of","with","by","from","that","this","is","are","was","were","be","been","being","have","has","had"]);
  
  const getSearchWords = (q: string) => {
    return q.split(/\s+/).filter(w => {
      const clean = w.toLowerCase().replace(/[^a-z0-9]/g, "");
      return clean.length > 2 && !stopWords.has(clean);
    });
  };

  const highlightMatch = (text: string, words: string[]) => {
    if (!words.length || !text) return <>{text}</>;
    // A simple regex approach to highlight matches:
    // Create a regex combining the search words
    const regex = new RegExp(`(${words.map(w => w.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')).join('|')})`, 'gi');
    const parts = text.split(regex);
    return (
      <>
        {parts.map((part, i) =>
          regex.test(part) ? <span key={i} className="bg-yellow-200 text-amber-900 font-semibold">{part}</span> : <React.Fragment key={i}>{part}</React.Fragment>
        )}
      </>
    );
  };

  useEffect(() => {
    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        const arr = Array.isArray(data) ? data : (data.transcript || data.entries || data.chunks || [data]);
        setEntries(arr);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [url]);

  if (loading) return <p className="text-sm text-[#999] p-8">Loading transcript...</p>;
  if (error) return <p className="text-sm text-[#dc2626] p-8">Failed to load transcript.</p>;

  const words = getSearchWords(searchQuote);

  useEffect(() => {
    if (!loading && containerRef.current && words.length > 0) {
      setTimeout(() => {
        const highlighted = containerRef.current?.querySelector('.bg-yellow-200');
        if (highlighted) {
          highlighted.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 300);
    }
  }, [loading, entries, words.length]);

  return (
    <div ref={containerRef} className="overflow-auto max-h-[calc(100vh-120px)] p-4 space-y-3">
      {entries.map((entry, i) => {
        const speaker = String(entry.speaker || entry.Speaker || "");
        let text = entry.text || entry.chunk_text || entry.content || entry.body || "";
        if (!text) {
          try { text = JSON.stringify(entry); } catch (e) { text = ""; }
        }
        text = String(text);
        const ts = entry.timestamp || entry.time || "";
        
        let hasMatch = false;
        if (words.length > 0) {
          const textLower = text.toLowerCase();
          hasMatch = words.some(w => textLower.includes(w.toLowerCase()));
        }

        return (
          <div key={i} className={`flex gap-3 ${speaker ? "" : "pl-0"} ${hasMatch ? "bg-yellow-50/50 p-2 border border-yellow-200 rounded" : ""}`}>
            {speaker && (
              <div className="shrink-0 w-28 text-right">
                <span className="text-[11px] font-semibold text-[#555] leading-relaxed">{speaker}</span>
                {ts && <p className="text-[10px] text-[#bbb] font-mono">{String(ts)}</p>}
              </div>
            )}
            <p className="text-[13px] text-[#333] leading-relaxed flex-1 border-l-2 border-[#e0e0e0] pl-3">
              {hasMatch ? highlightMatch(text, words) : text}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function CSVViewer({ url }: { url: string }) {
  const [rows, setRows] = useState<string[][]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(url)
      .then((r) => r.text())
      .then((text) => {
        const lines = text.split("\n").filter((l) => l.trim());
        setRows(lines.map((l) => l.split(",")));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [url]);

  if (loading) return <p className="text-sm text-[#999] p-8">Loading...</p>;

  return (
    <div className="overflow-auto max-h-[calc(100vh-120px)]">
      <table className="w-full text-xs font-mono border-collapse">
        <thead>
          <tr>
            {rows[0]?.map((cell, i) => (
              <th key={i} className="sticky top-0 bg-[#222] text-white px-3 py-2 text-left font-semibold whitespace-nowrap">
                {cell.trim()}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(1).map((row, ri) => (
            <tr key={ri} className={`border-b border-[#eee] ${ri % 2 === 0 ? "bg-white" : "bg-[#fafafa]"} hover:bg-[#fffbe6] transition-colors`}>
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-1.5 whitespace-nowrap text-[#333]">{cell.trim()}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type TabId = "document" | "graph";

export function SourceModal() {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<SourceInfo | null>(null);
  const [quote, setQuote] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sourceRef, setSourceRef] = useState("");
  const [activeTab, setActiveTab] = useState<TabId>("document");

  const handleOpen = useCallback((e: Event) => {
    const detail = (e as CustomEvent).detail;
    const ref = detail.ref as string;
    const company = (detail.company as string) || "IHCL";
    const q = (detail.quote as string) || "";

    setOpen(true);
    setLoading(true);
    setError(null);
    setSource(null);
    setQuote(q);
    setSourceRef(ref);
    setActiveTab("document");

    fetch(`/api/data/source?ref=${encodeURIComponent(ref)}&company=${encodeURIComponent(company)}`)
      .then((r) => {
        if (!r.ok) throw new Error("not found");
        return r.json();
      })
      .then((data) => setSource(data))
      .catch(() => setError(`Could not find document for: "${ref}"`))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    window.addEventListener("open-source", handleOpen);
    return () => window.removeEventListener("open-source", handleOpen);
  }, [handleOpen]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;

  // Build PDF search snippet — pick the most-specific 8-word window,
  // skipping generic filler at the start (articles, conjunctions, etc.)
  const searchSnippet = (() => {
    if (!quote) return null;
    const stopWords = new Set(["the","a","an","and","or","but","in","on","at","to","for","of","with","by","from","that","this","is","are","was","were","be","been","being","have","has","had"]);
    const words = quote.split(/\s+/).filter((w) => w.length > 0);
    // Find first non-stop-word position
    let start = words.findIndex((w) => !stopWords.has(w.toLowerCase().replace(/[^a-z]/g, "")));
    if (start < 0) start = 0;
    return words.slice(start, start + 10).join(" ");
  })();
  let pdfViewUrl: string | null = null;
  if (source?.pdfUrl) {
    const fragments: string[] = [];
    if (source.page) fragments.push(`page=${source.page}`);
    if (searchSnippet) fragments.push(`search=${encodeURIComponent(searchSnippet)}`);
    pdfViewUrl = source.pdfUrl + (fragments.length ? `#${fragments.join("&")}` : "");
  }

  return (
    <div className="fixed inset-0 z-9999 flex flex-col">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />

      {/* Modal */}
      <div className="relative z-10 flex flex-col m-4 sm:m-8 bg-white rounded-xl shadow-2xl overflow-hidden flex-1">
        {/* Header */}
        <div className="flex flex-col px-4 py-2.5 bg-white border-b border-[#e0e0e0] shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              {source && (
                <>
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                    source.type === "pdf" ? "text-[#dc2626] bg-[#fef2f2]" : "text-[#059669] bg-[#f0fdf4]"
                  }`}>
                    {source.type.toUpperCase()}
                  </span>
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-[#222] truncate">{source.label}</p>
                    <p className="text-[10px] text-[#999] truncate">{source.relativePath}</p>
                  </div>
                  {source.page && (
                    <span className="text-[10px] font-mono text-[#f59e0b] bg-[#fefce8] px-2 py-0.5 rounded font-semibold shrink-0">
                      Page {source.page}
                    </span>
                  )}
                </>
              )}
              {loading && <p className="text-sm text-[#999]">Locating document...</p>}
              {error && <p className="text-sm text-[#dc2626]">{error}</p>}
            </div>

            <button
              onClick={() => setOpen(false)}
              className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[#f0f0f0] transition-colors cursor-pointer text-[#888] hover:text-[#222]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
              </svg>
            </button>
          </div>

          {source && (
             <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-[#f0f0f0]">
               <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                 <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12h-2"/>
               </svg>
               <span className="text-[10px] text-[#2563eb] font-semibold tracking-wide uppercase">
                 Verified Origin: Document procured directly from BSEIndia.in &amp; Screener.in
               </span>
             </div>
          )}
        </div>

        {/* Quote banner */}
        {quote && source?.type === "pdf" && (
          <div className="bg-[#fef9c3] border-b border-[#fde68a] px-4 py-2 flex items-center gap-3 shrink-0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a16207" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <p className="text-[12px] text-[#78350f] italic truncate flex-1">
              &ldquo;{quote}&rdquo;
            </p>
            <button
              onClick={() => {
                navigator.clipboard.writeText(quote);
              }}
              className="shrink-0 px-2.5 py-1 text-[10px] font-semibold text-[#92400e] bg-[#fef3c7] border border-[#fde68a] rounded hover:bg-[#fde68a] transition-colors cursor-pointer whitespace-nowrap"
            >
              Copy text
            </button>
          </div>
        )}

        {/* Tab bar */}
        {source && !loading && (
          <div className="flex border-b border-[#e0e0e0] shrink-0 bg-white">
            {(["document", "graph"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-[12px] font-medium border-b-2 transition-colors cursor-pointer ${
                  activeTab === tab
                    ? "border-[#222] text-[#222]"
                    : "border-transparent text-[#999] hover:text-[#666]"
                }`}
              >
                {tab === "document" ? "Document" : "Graph Context"}
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-h-0">
          {activeTab === "document" && (
            <>
              {source?.type === "pdf" && pdfViewUrl && (
                <iframe src={pdfViewUrl} className="w-full h-full" title={source.label} />
              )}
              {source?.type === "csv" && source.csvUrl && (
                <div className="p-4">
                  {source.csvUrl.endsWith(".json")
                    ? <JSONTranscriptViewer url={source.csvUrl} searchQuote={quote} />
                    : <CSVViewer url={source.csvUrl} />}
                  <p className="text-[10px] text-[#999] mt-3">Source: {sourceRef}</p>
                </div>
              )}
            </>
          )}

          {activeTab === "graph" && source && (
            <div className="flex flex-col items-center justify-center h-full text-center px-8">
              <div className="w-16 h-16 rounded-full bg-[#f5f5f5] flex items-center justify-center mb-4">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="18" cy="6" r="3"/>
                  <path d="M8.5 7.5 15.5 16.5"/><path d="M15.5 7.5 8.5 16.5"/>
                </svg>
              </div>
              <h3 className="font-serif text-lg text-[#222] mb-2">Graph Context</h3>
              <p className="text-[13px] text-[#888] leading-relaxed max-w-sm mb-4">
                Visualize how this entity connects to other companies, sectors, and risk factors
                through our knowledge graph powered by Neo4j.
              </p>
              <span className="text-[11px] text-[#999] bg-[#fafafa] border border-[#e0e0e0] rounded-full px-3 py-1">
                Coming soon — Neo4j integration in progress
              </span>
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center h-full">
              <div className="w-8 h-8 border-2 border-[#e0e0e0] border-t-[#222] rounded-full animate-spin" />
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-[#999]">Document not available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
