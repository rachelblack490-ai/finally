"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtNum } from "@/lib/format";

interface PriceChartProps {
  ticker: string | null;
  values: number[];
}

// Main ticker chart — ticks since launch only (no history API).
export function PriceChart({ ticker, values }: PriceChartProps) {
  const data = values.map((v, i) => ({ i, price: v }));
  const rising = values.length >= 2 && values[values.length - 1] >= values[0];
  const stroke = rising ? "#16c784" : "#ea3943";
  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-bg-panel p-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-200">
          {ticker ?? "—"} <span className="text-xs text-gray-500">· ticks since launch</span>
        </h2>
        {values.length > 0 && (
          <span className="tabular text-sm text-gray-300">{fmtNum(values[values.length - 1])}</span>
        )}
      </div>
      <div className="min-h-0 flex-1">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-600">
            Waiting for ticks…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="i" hide />
              <YAxis
                domain={["auto", "auto"]}
                width={56}
                tick={{ fill: "#8b949e", fontSize: 11 }}
                tickFormatter={(v) => fmtNum(v)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a2e",
                  border: "1px solid #30363d",
                  borderRadius: 6,
                  color: "#e6edf3",
                }}
                formatter={(v: number) => [fmtNum(v), "Price"]}
                labelFormatter={() => ""}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke={stroke}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
