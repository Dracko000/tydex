"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BENCHMARKS } from "@/lib/data";

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--line)",
  borderRadius: 10,
  fontSize: 12,
  fontFamily: "var(--font-jb)",
  color: "var(--ink)",
} as const;

const axisTick = { fontSize: 11, fill: "var(--mut)", fontFamily: "var(--font-jb)" };

export function CalibrationCharts() {
  const ece = BENCHMARKS.map((b) => ({
    name: b.name,
    before: b.before,
    after: b.after,
  }));

  const acc = BENCHMARKS.map((b) => ({ name: b.name, accuracy: b.accuracy }));

  return (
    <div className="grid gap-12 lg:grid-cols-5">
      <div className="lg:col-span-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
            expected calibration error
          </p>
          <div className="flex items-center gap-4 font-mono text-xs text-mut">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-mut/45" aria-hidden />
              before
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-flame" aria-hidden />
              after
            </span>
          </div>
        </div>
        <div className="mt-4 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ece} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" strokeOpacity={0.5} />
              <XAxis
                dataKey="name"
                tick={axisTick}
                axisLine={{ stroke: "var(--line)" }}
                tickLine={false}
              />
              <YAxis
                domain={[0, 0.4]}
                tick={axisTick}
                tickFormatter={(v) => v.toFixed(2)}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "var(--brand-soft)", opacity: 0.6 }}
                contentStyle={tooltipStyle}
                labelStyle={{ color: "var(--ink)", fontWeight: 600 }}
              />
              <Bar
                dataKey="before"
                name="before"
                fill="var(--mut)"
                fillOpacity={0.45}
                radius={[5, 5, 0, 0]}
                maxBarSize={38}
                animationDuration={700}
              />
              <Bar
                dataKey="after"
                name="after"
                fill="var(--flame)"
                radius={[5, 5, 0, 0]}
                maxBarSize={38}
                animationDuration={700}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="lg:col-span-2">
        <p className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
          per-primitive accuracy
        </p>
        <div className="mt-4 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={acc} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" strokeOpacity={0.5} />
              <XAxis
                dataKey="name"
                tick={axisTick}
                axisLine={{ stroke: "var(--line)" }}
                tickLine={false}
              />
              <YAxis
                domain={[0, 1]}
                tick={axisTick}
                tickFormatter={(v) => v.toFixed(1)}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "var(--brand-soft)", opacity: 0.6 }}
                contentStyle={tooltipStyle}
                labelStyle={{ color: "var(--ink)", fontWeight: 600 }}
              />
              <Bar
                dataKey="accuracy"
                name="accuracy"
                fill="var(--brand)"
                radius={[5, 5, 0, 0]}
                maxBarSize={38}
                animationDuration={700}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}