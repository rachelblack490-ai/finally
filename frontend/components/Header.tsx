"use client";

import type { ConnStatus } from "@/lib/usePrices";
import type { Portfolio } from "@/lib/api";
import { fmtMoney } from "@/lib/format";

interface HeaderProps {
  portfolio: Portfolio | null;
  status: ConnStatus;
}

const STATUS_DOT: Record<ConnStatus, { color: string; label: string }> = {
  connected: { color: "#16c784", label: "Live" },
  connecting: { color: "#ecad0a", label: "Connecting" },
  reconnecting: { color: "#ecad0a", label: "Reconnecting" },
};

export function Header({ portfolio, status }: HeaderProps) {
  const dot = STATUS_DOT[status];
  const pl = portfolio?.unrealized_pl ?? 0;
  const plColor = pl > 0 ? "text-up" : pl < 0 ? "text-down" : "text-gray-400";
  return (
    <header className="flex items-center justify-between border-b border-gray-800 bg-bg-panel px-5 py-3">
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-bold text-finally-yellow">FinAlly</span>
        <span className="text-xs uppercase tracking-widest text-gray-500">
          Trading Workstation
        </span>
      </div>
      <div className="flex items-center gap-6 text-sm tabular">
        <Metric label="Total Value" value={fmtMoney(portfolio?.total_value)} />
        <Metric label="Cash" value={fmtMoney(portfolio?.cash)} />
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-wide text-gray-500">Unrealized P&amp;L</div>
          <div className={`font-semibold ${plColor}`}>{fmtMoney(pl)}</div>
        </div>
        <div className="flex items-center gap-2" title={dot.label}>
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: dot.color }}
            data-testid="status-dot"
          />
          <span className="text-xs text-gray-400">{dot.label}</span>
        </div>
      </div>
    </header>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-right">
      <div className="text-[10px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className="font-semibold text-gray-100">{value}</div>
    </div>
  );
}
