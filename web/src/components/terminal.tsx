"use client";

import { useEffect, useRef } from "react";

type Token = { type: "plain" | "prompt" | "out"; text: string };

export function Terminal({
  lines,
  prompt,
  className = "",
}: {
  lines: Token[];
  prompt: string;
  className?: string;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const shownRef = useRef(0);
  const doneRef = useRef(false);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      const all = el.querySelectorAll<HTMLElement>("[data-phase]");
      for (let i = 0; i < all.length; i++) all[i].style.opacity = "1";
      doneRef.current = true;
      return;
    }
    let raf = 0;
    const step = () => {
      const phases = el.querySelectorAll<HTMLElement>("[data-phase]");
      if (shownRef.current >= phases.length) {
        doneRef.current = true;
        return;
      }
      const p = phases[shownRef.current];
      p.style.opacity = "1";
      p.scrollIntoView({ block: "nearest" });
      shownRef.current += 1;
      raf = window.setTimeout(step, 160);
    };
    raf = window.setTimeout(step, 350);
    return () => window.clearTimeout(raf);
  }, []);

  return (
    <div
      ref={boxRef}
      role="img"
      aria-label="Example tydex choice call in a terminal"
      className={`rounded-2xl border border-line bg-surface shadow-xl shadow-brand/5 ${className}`}
    >
      <div className="flex items-center gap-1.5 border-b border-line px-4 py-3">
        <span className="h-3 w-3 rounded-full bg-raise" />
        <span className="h-3 w-3 rounded-full bg-raise" />
        <span className="h-3 w-3 rounded-full bg-raise" />
        <span className="ml-3 font-mono text-xs text-mut">tydex — zsh</span>
      </div>
      <div className="space-y-0 overflow-x-auto p-5 font-mono text-[13px] leading-6">
        {lines.map((line, i) => {
          if (line.type === "prompt") {
            return (
              <div key={i} data-phase className="opacity-0 transition-opacity duration-200">
                <span className="select-none text-brand">{prompt}</span>{" "}
                <span className="text-ink">{line.text}</span>
              </div>
            );
          }
          return (
            <div
              key={i}
              data-phase
              className="whitespace-pre opacity-0 transition-opacity duration-200"
              style={{ color: line.type === "out" ? "var(--tok-n)" : "var(--ink)" }}
            >
              {line.text}
            </div>
          );
        })}
        <div className="cursor text-ink" data-phase={undefined} />
      </div>
    </div>
  );
}