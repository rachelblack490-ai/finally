"use client";

import type { PriceMap, Position } from "@/lib/api";
import { fmtMoney, fmtNum, fmtPct } from "@/lib/format";

interface PositionsTableProps {
  positions: Position[];
  prices: PriceMap;
  onSelect: (ticker: string) => void;
}

export function PositionsTable({ positions, prices, onSelect }: PositionsTableProps) {
  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-bg-panel">
      <h2 className="border-b border-gray-800 px-3 py-2 text-sm font-semibold text-gray-200">
        Positions
      </h2>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-bg-panel text-[10px] uppercase tracking-wide text-gray-500">
            <tr>
              <th className="px-3 py-1.5 text-left">Ticker</th>
              <th className="px-3 py-1.5 text-right">Qty</th>
              <th className="px-3 py-1.5 text-right">Avg</th>
              <th className="px-3 py-1.5 text-right">Last</th>
              <th className="px-3 py-1.5 text-right">Value</th>
              <th className="px-3 py-1.5 text-right">P&amp;L</th>
              <th className="px-3 py-1.5 text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-gray-600">
                  No open positions
                </td>
              </tr>
            ) : (
              positions.map((p) => {
                const last = prices[p.ticker]?.price ?? p.price;
                const pl = p.unrealized_pl;
                const plClass = pl > 0 ? "text-up" : pl < 0 ? "text-down" : "text-gray-400";
                return (
                  <tr
                    key={p.ticker}
                    onClick={() => onSelect(p.ticker)}
                    className="cursor-pointer border-t border-gray-800/60 tabular hover:bg-white/5"
                    data-testid={`pos-row-${p.ticker}`}
                  >
                    <td className="px-3 py-1.5 text-left font-semibold text-gray-100">{p.ticker}</td>
                    <td className="px-3 py-1.5 text-right text-gray-300">{fmtNum(p.quantity, 4)}</td>
                    <td className="px-3 py-1.5 text-right text-gray-400">{fmtNum(p.avg_cost)}</td>
                    <td className="px-3 py-1.5 text-right text-gray-200">{fmtNum(last)}</td>
                    <td className="px-3 py-1.5 text-right text-gray-200">{fmtMoney(p.market_value)}</td>
                    <td className={`px-3 py-1.5 text-right ${plClass}`}>{fmtMoney(pl)}</td>
                    <td className={`px-3 py-1.5 text-right ${plClass}`}>
                      {fmtPct(p.unrealized_pl_percent)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
