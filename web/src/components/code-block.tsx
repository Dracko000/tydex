"use client";

import { useState } from "react";

export function CodeBlock({
  label,
  code,
  output,
}: {
  label: string;
  code: string;
  output?: string;
}) {
  const [showOut, setShowOut] = useState(false);

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <span className="font-mono text-xs font-medium text-mut">{label}</span>
        <button
          type="button"
          onClick={() => setShowOut((v) => !v)}
          aria-pressed={showOut}
          className="cursor-pointer rounded-lg border border-line px-2.5 py-1 font-mono text-xs text-mut transition-colors duration-200 hover:text-brand"
        >
          {showOut ? "hide output" : "show output"}
        </button>
      </div>
      <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-6">
        <code className="text-ink">{code}</code>
      </pre>
      {showOut ? (
        <pre className="border-t border-line bg-raise/60 p-5 font-mono text-[13px] leading-6">
          <code className="text-tk-n">{output}</code>
        </pre>
      ) : null}
    </div>
  );
}