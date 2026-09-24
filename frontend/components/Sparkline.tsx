"use client";

interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
}

// Lightweight inline-SVG sparkline (ticks since launch). Recharts is reserved
// for the larger charts; a per-row SVG polyline keeps the watchlist fast.
export function Sparkline({ values, width = 96, height = 24 }: SparklineProps) {
  if (!values || values.length < 2) {
    return <svg width={width} height={height} aria-hidden="true" />;
  }
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const step = width / (values.length - 1);
  const points = values
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - lo) / span) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const rising = values[values.length - 1] >= values[0];
  const stroke = rising ? "#16c784" : "#ea3943";
  return (
    <svg width={width} height={height} className="overflow-visible" aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
