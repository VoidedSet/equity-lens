"use client";

import React, { useState, useRef } from "react";

interface HighlightProps {
  children: React.ReactNode;
  quote: string;
  refName: string;
  company?: string;
  citationText: string;
}

export function Highlight({ children, quote, refName, company = "IHCL", citationText }: HighlightProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const triggerRef = useRef<HTMLSpanElement>(null);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.dispatchEvent(
      new CustomEvent("open-source", {
        detail: {
          ref: refName,
          company,
          quote,
        },
      })
    );
  };

  return (
    <span className="relative inline group">
      <span
        ref={triggerRef}
        onClick={handleClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="cursor-pointer bg-[#fef9c3]/60 hover:bg-[#fde68a] border-b border-[#f59e0b]/50 hover:border-[#f59e0b] text-inherit transition-all rounded-sm"
      >
        {children}
      </span>

      {showTooltip && (
        <span className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs bg-[#222] text-white text-[11px] leading-tight px-3 py-2 rounded-md shadow-xl pointer-events-none block">
          <span className="font-bold text-white/60 mb-1 uppercase tracking-wider text-[9px] block">Source Citation</span>
          <span className="block">{citationText}</span>
          <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[#222] block" />
        </span>
      )}
    </span>
  );
}
