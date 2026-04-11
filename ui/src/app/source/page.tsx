"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

type SourceInfo = {
  type: "pdf" | "csv";
  relativePath: string;
  page: number | null;
  searchText: string | null;
  label: string;
  pdfUrl: string | null;
  csvUrl: string | null;
};

function CSVViewer({ url, sourceRef }: { url: string; sourceRef: string }) {
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

  if (loading) return <p className="text-sm text-[#94a3b8] p-8">Loading CSV...</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono border-collapse">
        <thead>
          <tr>
            {rows[0]?.map((cell, i) => (
              <th
                key={i}
                className="sticky top-0 bg-[#0f172a] text-white px-3 py-2 text-left font-semibold whitespace-nowrap"
              >
                {cell.trim()}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(1).map((row, ri) => (
            <tr
              key={ri}
              className={`border-b border-[#f1f5f9] ${
                ri % 2 === 0 ? "bg-white" : "bg-[#f8fafc]"
              } hover:bg-[#fef9c3] transition-colors`}
            >
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-1.5 whitespace-nowrap text-[#334155]">
                  {cell.trim()}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[10px] text-[#94a3b8] mt-4 px-2">
        Source: {sourceRef} &middot; Actual data file from Screener.in extraction
      </p>
    </div>
  );
}

function SourceViewer() {
  const searchParams = useSearchParams();
  const ref = searchParams.get("ref") || "";
  const company = searchParams.get("company") || "IHCL";
  const quote = searchParams.get("q") || "";
  const [source, setSource] = useState<SourceInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ref) {
      setError("No source reference provided.");
      setLoading(false);
      return;
    }
    fetch(`/api/data/source?ref=${encodeURIComponent(ref)}&company=${encodeURIComponent(company)}`)
      .then((r) => {
        if (!r.ok) throw new Error("Source not found");
        return r.json();
      })
      .then((data) => setSource(data))
      .catch(() => setError(`Could not find document for: "${ref}"`))
      .finally(() => setLoading(false));
  }, [ref, company]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fafafa]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#e2e8f0] border-t-[#0f172a] rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-[#94a3b8]">Locating source document...</p>
        </div>
      </div>
    );
  }

  if (error || !source) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fafafa]">
        <div className="text-center max-w-md">
          <div className="w-12 h-12 rounded-full bg-[#fef2f2] flex items-center justify-center mx-auto mb-4">
            <span className="text-[#dc2626] text-lg">!</span>
          </div>
          <p className="text-sm text-[#dc2626] mb-2 font-medium">Document not found</p>
          <p className="text-xs text-[#94a3b8] mb-4">{error}</p>
          <Link
            href="/"
            className="inline-block px-4 py-2 text-sm text-white bg-[#0f172a] rounded-lg hover:bg-[#1e293b]"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // Build the PDF URL with combined page + search fragment
  // Chrome/Edge PDF viewer supports: #page=N&search=TERM
  // Use first ~8 words of quote for search to avoid URL length issues
  const searchSnippet = quote
    ? quote.split(/\s+/).slice(0, 8).join(" ")
    : null;

  let pdfViewUrl: string | null = null;
  if (source.pdfUrl) {
    const fragments: string[] = [];
    if (source.page) fragments.push(`page=${source.page}`);
    if (searchSnippet) fragments.push(`search=${encodeURIComponent(searchSnippet)}`);
    pdfViewUrl = source.pdfUrl + (fragments.length ? `#${fragments.join("&")}` : "");
  }

  return (
    <div className="min-h-screen bg-[#fafafa] flex flex-col">
      {/* Header bar */}
      <div className="sticky top-0 z-50 bg-white border-b border-[#e2e8f0] shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-xs text-[#94a3b8] hover:text-[#0f172a] transition-colors"
            >
              &larr; Dashboard
            </Link>
            <div className="h-4 w-px bg-[#e2e8f0]" />
            <div>
              <p className="text-[13px] font-semibold text-[#0f172a]">{source.label}</p>
              <p className="text-[10px] text-[#94a3b8]">{source.relativePath}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {source.page && (
              <span className="text-[10px] font-mono text-[#f59e0b] bg-[#fefce8] px-2 py-1 rounded font-semibold">
                Page {source.page}
              </span>
            )}
            <span
              className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded ${
                source.type === "pdf"
                  ? "text-[#dc2626] bg-[#fef2f2]"
                  : "text-[#059669] bg-[#f0fdf4]"
              }`}
            >
              {source.type.toUpperCase()}
            </span>
            {pdfViewUrl && (
              <a
                href={pdfViewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-[#2563eb] hover:underline"
              >
                Open in new tab &rarr;
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Quote banner — shows what text to find in the document */}
      {quote && source.type === "pdf" && (
        <div className="bg-[#fef9c3] border-b border-[#fde68a] px-4 py-2.5 flex items-start gap-3">
          <div className="shrink-0 mt-0.5">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a16207" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-semibold text-[#92400e] uppercase tracking-wide mb-0.5">
              Find this text in the document
            </p>
            <p className="text-[13px] text-[#78350f] leading-relaxed italic truncate">
              &ldquo;{quote}&rdquo;
            </p>
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(quote);
              const btn = document.getElementById("copy-quote-btn");
              if (btn) { btn.textContent = "Copied!"; setTimeout(() => { btn.textContent = "Copy & Ctrl+F"; }, 1500); }
            }}
            id="copy-quote-btn"
            className="shrink-0 px-3 py-1.5 text-[11px] font-semibold text-[#92400e] bg-[#fef3c7] border border-[#fde68a] rounded-md hover:bg-[#fde68a] transition-colors cursor-pointer whitespace-nowrap"
          >
            Copy &amp; Ctrl+F
          </button>
        </div>
      )}

      {/* Document content */}
      <div className="flex-1">
        {source.type === "pdf" && pdfViewUrl && (
          <iframe
            src={pdfViewUrl}
            className={`w-full ${quote ? "h-[calc(100vh-100px)]" : "h-[calc(100vh-52px)]"}`}
            title={source.label}
          />
        )}

        {source.type === "csv" && source.csvUrl && (
          <div className="max-w-7xl mx-auto p-4">
            <CSVViewer url={source.csvUrl} sourceRef={ref} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function SourcePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-sm text-[#94a3b8]">Loading...</p>
        </div>
      }
    >
      <SourceViewer />
    </Suspense>
  );
}
