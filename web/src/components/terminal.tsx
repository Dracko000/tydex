"use client";

import { motion, useReducedMotion } from "framer-motion";

type Token = { type: "plain" | "prompt" | "out"; text: string };

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.11, delayChildren: 0.25 } },
};

const item = {
  hidden: { opacity: 0, y: 4 },
  show: { opacity: 1, y: 0, transition: { duration: 0.22 } },
};

export function Terminal({
  lines,
  prompt,
  className = "",
}: {
  lines: Token[];
  prompt: string;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const state = reduce ? ("show" as const) : undefined;

  return (
    <div
      role="img"
      aria-label="Example tydex choice call in a terminal"
      className={`rounded-xl border border-line bg-surface shadow-xl shadow-brand/5 ${className}`}
    >
      <div className="flex items-center gap-1.5 border-b border-line px-4 py-3">
        <span className="h-3 w-3 rounded-full bg-raise" />
        <span className="h-3 w-3 rounded-full bg-raise" />
        <span className="h-3 w-3 rounded-full bg-raise" />
        <span className="ml-3 font-mono text-xs text-mut">tydex — zsh</span>
      </div>
      <motion.div
        variants={container}
        initial={state ?? "hidden"}
        animate={state ?? "show"}
        className="overflow-x-auto p-5 font-mono text-[13px] leading-6"
      >
        {lines.map((line, i) =>
          line.type === "prompt" ? (
            <motion.div key={i} variants={item}>
              <span className="select-none text-brand">{prompt}</span>{" "}
              <span className="text-ink">{line.text}</span>
            </motion.div>
          ) : (
            <motion.div
              key={i}
              variants={item}
              className="whitespace-pre"
              style={{ color: line.type === "out" ? "var(--tk-n)" : "var(--ink)" }}
            >
              {line.text}
            </motion.div>
          )
        )}
        <div className="cursor text-ink" />
      </motion.div>
    </div>
  );
}