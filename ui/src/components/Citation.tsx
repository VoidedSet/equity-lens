"use client";

export function Citation({ source }: { source: string }) {
  return (
    <span className="citation inline-flex items-center gap-1">
      <svg width="10" height="10" viewBox="0 0 16 16" fill="none" className="opacity-50">
        <path d="M4 6H2a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2zm0 0V4a4 4 0 0 1 4-4M12 6h-2a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2zm0 0V4a4 4 0 0 1 4-4" stroke="currentColor" strokeWidth="1.5"/>
      </svg>
      {source}
    </span>
  );
}
