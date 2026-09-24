"use client";

import { useState } from "react";
import type { PriceMap, WatchlistItem } from "@/lib/api";
import { fmtNum, fmtPct, sessionChangePct } from "@/lib/format";
import { Sparkline } from "./Sparkline";

interface WatchlistProps {
  items: WatchlistItem[];
  prices: PriceMap;
  sessionOpen: Record<string, number>;
  histories: Record<string, number[]>;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
  onAdd: (ticker: string) => void;
}

export function Watchlist({
  items,
  prices,
  sessionOpen,
  histories,
  selected,
  onSelect,
  onRemove,
  onAdd,
}: WatchlistProps) {
  const [newTicker, setNewTicker] = useState("");

  function submitAdd(e: React.FormEvent) {
    e.preventDefault();
    const t = newTicker.trim().toUpperCase();
    if (t) {
      onAdd(t);
      setNewTicker("");
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
          Watchlist
        </h2>
      </div>
      <form onSubmit={submitAdd} className="flex gap-2 px-3 pb-2">
        <input
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          placeholder="Add ticker"
          aria-label="Add ticker"
          className="w-full rounded border border-gray-700 bg-bg px-2 py-1 text-sm uppercase text-gray-100 outline-none focus:border-finally-blue"
        />
        <button
          type="submit"
          className="rounded bg-finally-blue px-3 py-1 text-sm font-semibold text-white hover:opacity-90"
        >
          Add
        </button>
      </form>
      <div className="flex-1 overflow-y-auto">
        {items.map((item) => {
          const tick = prices[item.ticker];
          const price = tick?.price ?? item.price ?? null;
          const open = sessionOpen[item.ticker];
          const changePct =
            price !== null && open !== undefined ? sessionChangePct(price, open) : null;
          const direction = tick?.direction ?? "flat";
          const isSel = selected === item.ticker;
          const flashClass =
            direction === "up"
              ? "animate-flashUp"
              : direction === "down"
                ? "animate-flashDown"
                : "";
          return (
            <div
              key={item.ticker}
              onClick={() => onSelect(item.ticker)}
              className={`group flex cursor-pointer items-center gap-2 border-l-2 px-3 py-2 ${
                isSel
                  ? "border-finally-yellow bg-white/5"
                  : "border-transparent hover:bg-white/5"
              }`}
              data-testid={`wl-row-${item.ticker}`}
            >
              <div className="w-14 shrink-0 font-semibold text-gray-100">{item.ticker}</div>
              <div className="w-20 shrink-0 text-right tabular">
                <span
                  key={price ?? 0}
                  className={`rounded px-1 ${flashClass}`}
                  data-testid={`wl-price-${item.ticker}`}
                >
                  {price !== null ? fmtNum(price) : "—"}
                </span>
              </div>
              <div
                className={`w-16 shrink-0 text-right tabular text-xs ${
                  changePct === null
                    ? "text-gray-500"
                    : changePct > 0
                      ? "text-up"
                      : changePct < 0
                        ? "text-down"
                        : "text-gray-400"
                }`}
              >
                {changePct !== null ? fmtPct(changePct) : "—"}
              </div>
              <div className="flex-1">
                <Sparkline values={histories[item.ticker] ?? []} />
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(item.ticker);
                }}
                aria-label={`Remove ${item.ticker}`}
                className="w-5 shrink-0 text-gray-600 opacity-0 hover:text-down group-hover:opacity-100"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
