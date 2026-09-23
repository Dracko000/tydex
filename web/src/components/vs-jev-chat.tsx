"use client";

import { motion, useReducedMotion } from "framer-motion";
import { VS_JEV } from "@/lib/data";

const wrap = {
  hidden: {},
  show: { transition: { staggerChildren: 0.14, delayChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
};

const COLUMNS = [
  {
    side: "jev",
    name: "Jev",
    sub: "original · closed SaaS",
    bubble: "bg-raise text-ink",
    answerOf: (r: (typeof VS_JEV)[number]) => r.jev,
  },
  {
    side: "tydex",
    name: "tydex",
    sub: "open-source clone",
    bubble: "border border-brand/25 bg-brand-soft text-ink",
    answerOf: (r: (typeof VS_JEV)[number]) => r.tydex,
  },
] as const;

export function VsJevChat() {
  const reduce = useReducedMotion();
  const state = reduce ? undefined : ("show" as const);

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      {COLUMNS.map((col) => (
        <div
          key={col.side}
          className="overflow-hidden rounded-xl border border-line bg-surface shadow-xl shadow-brand/5"
        >
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <span className="font-mono text-sm font-semibold tracking-wider text-ink uppercase">
              {col.name}
            </span>
            <span className="font-mono text-xs text-mut">{col.sub}</span>
          </div>
          <motion.ul
            variants={wrap}
            initial={state ?? "hidden"}
            animate={state ?? "show"}
            className="space-y-5 p-5"
          >
            {VS_JEV.map((r, i) => (
              <motion.li key={r.q} variants={item} className="space-y-2">
                <p className="flex items-baseline gap-2 font-mono text-xs text-mut">
                  <span className="text-brand/70">Q{i + 1} ·</span>
                  {r.q}
                </p>
                <p className={`rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-6 ${col.bubble}`}>
                  {col.answerOf(r)}
                </p>
              </motion.li>
            ))}
          </motion.ul>
        </div>
      ))}
    </div>
  );
}