"use client";

import { useState } from "react";

export function CodeBlock({
  label,
  code,
  output,
  hideToggle = false,
  noPad = false,
}: {
  label: string;
  code: string;
  output?: string;
  hideToggle?: boolean;
  noPad?: boolean;
}) {
  const [showOut, setShowOut] = useState(false);

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface">
      <div
        className={`flex items-center justify-between ${noPad ? "px-4 py-2" : "border-b border-line px-4 py-2.5"}`}
      >
        <span className="font-mono text-xs font-medium text-mut">{label}</span>
        {output && !hideToggle ? (
          <button
            type="button"
            onClick={() => setShowOut((v) => !v)}
            aria-pressed={showOut}
            className="cursor-pointer font-mono text-xs text-mut transition-colors duration-200 hover:text-brand"
          >
            {showOut ? "hide output" : "show output"}
          </button>
        ) : null}
      </div>
      <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-6">
        <code className="text-ink">{code}</code>
      </pre>
      {showOut ? (
        <div className="border-t border-line/60 px-5 py-4">
          <div className="mb-2 font-mono text-[11px] tracking-widest text-mut uppercase">
            output
          </div>
          <pre className="overflow-x-auto font-mono text-[13px] leading-6">
            <code className="text-tk-n">{output}</code>
          </pre>
        </div>
      ) : null}
    </div>
  );
}