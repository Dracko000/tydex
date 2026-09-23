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
import { VS_JEV_SCORES } from "@/lib/data";

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--line)",
  borderRadius: 10,
  fontSize: 12,
  fontFamily: "var(--font-jb)",
  color: "var(--ink)",
} as const;

const tick = { fontSize: 11, fill: "var(--mut)", fontFamily: "var(--font-jb)" };

export function VsJevChart() {
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-mono text-xs font-semibold tracking-widest text-mut uppercase">
          capability coverage · 0–10 illustrative
        </p>
        <div className="flex items-center gap-4 font-mono text-xs text-mut">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-brand" aria-hidden />
            tydex
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-mut/45" aria-hidden />
            Jev
          </span>
        </div>
      </div>
      <div className="mt-4 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={VS_JEV_SCORES}
            layout="vertical"
            margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
          >
            <CartesianGrid horizontal={false} stroke="var(--line)" strokeOpacity={0.5} />
            <XAxis
              type="number"
              domain={[0, 10]}
              tick={tick}
              tickCount={6}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="cat"
              width={172}
              tick={tick}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "var(--brand-soft)", opacity: 0.6 }}
              contentStyle={tooltipStyle}
              labelStyle={{ color: "var(--ink)", fontWeight: 600 }}
            />
            <Bar
              dataKey="tydex"
              name="tydex"
              fill="var(--brand)"
              radius={[0, 4, 4, 0]}
              barSize={12}
              animationDuration={700}
            />
            <Bar
              dataKey="jev"
              name="Jev"
              fill="var(--mut)"
              fillOpacity={0.45}
              radius={[0, 4, 4, 0]}
              barSize={12}
              animationDuration={700}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}