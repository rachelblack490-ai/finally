"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  YAxis,
} from "recharts";
import type { Snapshot } from "@/lib/api";
import { fmtMoney } from "@/lib/format";

interface PnLChartProps {
  snapshots: Snapshot[];
}

export function PnLChart({ snapshots }: PnLChartProps) {
  const data = snapshots.map((s, i) => ({ i, value: s.total_value }));
  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-bg-panel p-3">
      <h2 className="mb-2 text-sm font-semibold text-gray-200">Portfolio Value</h2>
      <div className="min-h-0 flex-1">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-600">
            Building history…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 5, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="pnl" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#209dd7" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#209dd7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <YAxis
                domain={["auto", "auto"]}
                width={64}
                tick={{ fill: "#8b949e", fontSize: 11 }}
                tickFormatter={(v) => `$${Math.round(v / 100) / 10}k`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a2e",
                  border: "1px solid #30363d",
                  borderRadius: 6,
                  color: "#e6edf3",
                }}
                formatter={(v: number) => [fmtMoney(v), "Total"]}
                labelFormatter={() => ""}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#209dd7"
                strokeWidth={2}
                fill="url(#pnl)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
