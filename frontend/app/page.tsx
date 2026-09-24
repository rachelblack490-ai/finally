"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type ChatMessage,
  type Portfolio,
  type Snapshot,
  type WatchlistItem,
} from "@/lib/api";
import { usePrices } from "@/lib/usePrices";
import { Header } from "@/components/Header";
import { Watchlist } from "@/components/Watchlist";
import { PriceChart } from "@/components/PriceChart";
import { PnLChart } from "@/components/PnLChart";
import { Heatmap } from "@/components/Heatmap";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { ChatPanel } from "@/components/ChatPanel";

export default function Page() {
  const { prices, sessionOpen, histories, status } = usePrices();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tradeBusy, setTradeBusy] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;

  const refreshPortfolio = useCallback(async () => {
    try {
      setPortfolio(await api.getPortfolio());
    } catch {
      /* transient */
    }
  }, []);

  const refreshWatchlist = useCallback(async () => {
    try {
      const wl = await api.getWatchlist();
      setWatchlist(wl);
      if (!selectedRef.current && wl.length > 0) setSelected(wl[0].ticker);
    } catch {
      /* transient */
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      setHistory(await api.getHistory());
    } catch {
      /* transient */
    }
  }, []);

  const refreshChat = useCallback(async () => {
    try {
      setChat(await api.getChatHistory());
    } catch {
      /* transient */
    }
  }, []);

  useEffect(() => {
    refreshPortfolio();
    refreshWatchlist();
    refreshHistory();
    refreshChat();
    const id = setInterval(() => {
      refreshPortfolio();
      refreshWatchlist();
      refreshHistory();
    }, 4000);
    return () => clearInterval(id);
  }, [refreshPortfolio, refreshWatchlist, refreshHistory, refreshChat]);

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const onTrade = useCallback(
    async (ticker: string, quantity: number, side: "buy" | "sell") => {
      setTradeBusy(true);
      try {
        const res = await api.trade(ticker, quantity, side);
        flash(res.message);
        await Promise.all([refreshPortfolio(), refreshWatchlist(), refreshHistory()]);
      } catch (e) {
        flash(e instanceof Error ? e.message : "Trade failed");
      } finally {
        setTradeBusy(false);
      }
    },
    [refreshPortfolio, refreshWatchlist, refreshHistory],
  );

  const onAddWatchlist = useCallback(
    async (ticker: string) => {
      try {
        await api.addWatchlist(ticker);
        setSelected(ticker);
        await refreshWatchlist();
      } catch (e) {
        flash(e instanceof Error ? e.message : "Could not add ticker");
      }
    },
    [refreshWatchlist],
  );

  const onRemoveWatchlist = useCallback(
    async (ticker: string) => {
      try {
        await api.removeWatchlist(ticker);
        await refreshWatchlist();
        if (selectedRef.current === ticker) setSelected(null);
      } catch {
        flash("Could not remove ticker");
      }
    },
    [refreshWatchlist],
  );

  const onSendChat = useCallback(
    async (message: string) => {
      setChatBusy(true);
      setChatError(null);
      // Optimistically show the user's turn.
      setChat((c) => [
        ...c,
        { role: "user", content: message, actions: null, created_at: "" },
      ]);
      try {
        await api.chat(message);
        await Promise.all([
          refreshChat(),
          refreshPortfolio(),
          refreshWatchlist(),
          refreshHistory(),
        ]);
      } catch (e) {
        setChatError(e instanceof Error ? e.message : "Chat failed");
      } finally {
        setChatBusy(false);
      }
    },
    [refreshChat, refreshPortfolio, refreshWatchlist, refreshHistory],
  );

  const selectedHistory = selected ? histories[selected] ?? [] : [];

  return (
    <div className="flex h-screen flex-col bg-bg text-gray-100">
      <Header portfolio={portfolio} status={status} />
      <main className="grid min-h-0 flex-1 grid-cols-[320px_1fr_380px] gap-3 p-3">
        {/* Left: watchlist */}
        <section className="min-h-0 rounded-lg border border-gray-800 bg-bg-panel">
          <Watchlist
            items={watchlist}
            prices={prices}
            sessionOpen={sessionOpen}
            histories={histories}
            selected={selected}
            onSelect={setSelected}
            onRemove={onRemoveWatchlist}
            onAdd={onAddWatchlist}
          />
        </section>

        {/* Center: chart, trade bar, positions */}
        <section className="grid min-h-0 grid-rows-[1fr_auto_minmax(180px,1fr)] gap-3">
          <div className="min-h-0">
            <PriceChart ticker={selected} values={selectedHistory} />
          </div>
          <TradeBar ticker={selected} onTrade={onTrade} busy={tradeBusy} />
          <div className="min-h-0">
            <PositionsTable
              positions={portfolio?.positions ?? []}
              prices={prices}
              onSelect={setSelected}
            />
          </div>
        </section>

        {/* Right: heatmap, P&L, chat */}
        <section className="grid min-h-0 grid-rows-[minmax(150px,1fr)_minmax(150px,1fr)_minmax(200px,1.4fr)] gap-3">
          <div className="min-h-0">
            <Heatmap positions={portfolio?.positions ?? []} />
          </div>
          <div className="min-h-0">
            <PnLChart snapshots={history} />
          </div>
          <div className="min-h-0">
            <ChatPanel
              messages={chat}
              onSend={onSendChat}
              busy={chatBusy}
              error={chatError}
              collapsed={chatCollapsed}
              onToggle={() => setChatCollapsed((c) => !c)}
            />
          </div>
        </section>
      </main>
      {toast && (
        <div
          className="fixed bottom-4 left-1/2 -translate-x-1/2 rounded-lg border border-gray-700 bg-bg-panel px-4 py-2 text-sm text-gray-100 shadow-lg"
          data-testid="toast"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
