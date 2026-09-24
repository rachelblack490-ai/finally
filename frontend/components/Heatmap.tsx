"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import type { Position } from "@/lib/api";
import { fmtMoney, fmtPct } from "@/lib/format";

interface HeatmapProps {
  positions: Position[];
}

function plColor(pct: number): string {
  // Green for gains, red for losses; intensity scales with magnitude.
  const clamped = Math.max(-5, Math.min(5, pct));
  const intensity = Math.min(1, Math.abs(clamped) / 5);
  if (clamped >= 0) {
    const g = Math.round(60 + intensity * 140);
    return `rgb(22, ${g}, 90)`;
  }
  const r = Math.round(120 + intensity * 114);
  return `rgb(${r}, 57, 67)`;
}

interface CellProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  plPct?: number;
}

function Cell({ x = 0, y = 0, width = 0, height = 0, name, plPct = 0 }: CellProps) {
  if (width <= 0 || height <= 0) return null;
  const show = width > 46 && height > 26;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={3}
        style={{ fill: plColor(plPct), stroke: "#0d1117", strokeWidth: 2 }}
      />
      {show && name && (
        <>
          <text x={x + 6} y={y + 18} fill="#fff" fontSize={12} fontWeight={700}>
            {name}
          </text>
          <text x={x + 6} y={y + 33} fill="#e6edf3" fontSize={11}>
            {fmtPct(plPct)}
          </text>
        </>
      )}
    </g>
  );
}

export function Heatmap({ positions }: HeatmapProps) {
  const data = positions.map((p) => ({
    name: p.ticker,
    size: Math.max(p.market_value, 0.01),
    plPct: p.unrealized_pl_percent,
  }));

  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-bg-panel p-3">
      <h2 className="mb-2 text-sm font-semibold text-gray-200">
        Holdings Heatmap <span className="text-xs text-gray-500">· size = weight, color = P&amp;L</span>
      </h2>
      <div className="min-h-0 flex-1">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-600">
            No positions yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              stroke="#0d1117"
              isAnimationActive={false}
              content={<Cell />}
            />
          </ResponsiveContainer>
        )}
      </div>
      <div className="mt-1 text-right text-xs text-gray-500">
        {positions.length} position{positions.length === 1 ? "" : "s"} ·{" "}
        {fmtMoney(positions.reduce((s, p) => s + p.market_value, 0))}
      </div>
    </div>
  );
}
