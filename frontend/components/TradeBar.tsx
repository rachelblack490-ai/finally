"use client";

import { useEffect, useState } from "react";

interface TradeBarProps {
  ticker: string | null;
  onTrade: (ticker: string, quantity: number, side: "buy" | "sell") => Promise<void>;
  busy: boolean;
}

export function TradeBar({ ticker, onTrade, busy }: TradeBarProps) {
  const [symbol, setSymbol] = useState(ticker ?? "");
  const [qty, setQty] = useState("1");

  useEffect(() => {
    if (ticker) setSymbol(ticker);
  }, [ticker]);

  async function submit(side: "buy" | "sell") {
    const t = symbol.trim().toUpperCase();
    const q = parseFloat(qty);
    if (!t || !q || q <= 0) return;
    await onTrade(t, q, side);
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-800 bg-bg-panel px-4 py-3">
      <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">Trade</span>
      <input
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        placeholder="Ticker"
        aria-label="Trade ticker"
        className="w-24 rounded border border-gray-700 bg-bg px-2 py-1.5 text-sm uppercase text-gray-100 outline-none focus:border-finally-blue"
      />
      <input
        value={qty}
        onChange={(e) => setQty(e.target.value)}
        type="number"
        min="0"
        step="any"
        aria-label="Trade quantity"
        className="w-24 rounded border border-gray-700 bg-bg px-2 py-1.5 text-sm tabular text-gray-100 outline-none focus:border-finally-blue"
      />
      <button
        onClick={() => submit("buy")}
        disabled={busy}
        className="rounded bg-up px-5 py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        data-testid="buy-btn"
      >
        Buy
      </button>
      <button
        onClick={() => submit("sell")}
        disabled={busy}
        className="rounded bg-down px-5 py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        data-testid="sell-btn"
      >
        Sell
      </button>
    </div>
  );
}
