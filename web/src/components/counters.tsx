"use client";

import { useEffect, useRef, useState } from "react";

export function Counter({
  value,
  suffix = "",
  label,
}: {
  value: number;
  suffix?: string;
  label: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [display, setDisplay] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduced = () =>
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries[0].isIntersecting || started.current) return;
        started.current = true;
        setDisplay((prev) => (reduced() ? value : prev));
        if (reduced()) {
          io.disconnect();
          return;
        }
        const t0 = performance.now();
        const dur = 800;
        const tick = (t: number) => {
          const p = Math.min(1, (t - t0) / dur);
          const eased = 1 - Math.pow(1 - p, 3);
          setDisplay(Math.round(value * eased));
          if (p < 1) requestAnimationFrame(tick);
          else io.disconnect();
        };
        requestAnimationFrame(tick);
      },
      { threshold: 0.5 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [value]);

  return (
    <div ref={ref} className="text-center">
      <div className="font-mono text-4xl font-semibold tracking-tight text-brand tabular-nums">
        {display}
        {suffix}
      </div>
      <div className="mt-2 text-sm text-mut">{label}</div>
    </div>
  );
}