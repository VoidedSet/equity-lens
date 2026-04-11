"use client";

import { useRef } from "react";

export function Citation({
  source,
  company,
  quote,
  inline,
}: {
  source: string;
  company?: string;
  quote?: string;
  inline?: boolean;
}) {
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const openModal = () => {
    window.dispatchEvent(
      new CustomEvent("open-source", {
        detail: { ref: source, company: company || "IHCL", quote: quote || "" },
      })
    );
  };

  const handleHoverEnter = () => {
    hoverTimeout.current = setTimeout(() => openModal(), 400);
  };

  const handleHoverLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  };

  if (inline) {
    return (
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); openModal(); }}
        onMouseEnter={handleHoverEnter}
        onMouseLeave={handleHoverLeave}
        className="inline-flex items-center gap-0.5 text-[#6b7280] hover:text-[#1a1a1a] transition-colors cursor-pointer align-baseline"
        title={`View source: ${source}`}
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-60">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
        </svg>
      </button>
    );
  }

  return (
    <button
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); openModal(); }}
      onMouseEnter={handleHoverEnter}
      onMouseLeave={handleHoverLeave}
      className="citation inline-flex items-center gap-1 transition-colors cursor-pointer"
      title={`View source: ${source}`}
    >
      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-50">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
      {source}
    </button>
  );
}
