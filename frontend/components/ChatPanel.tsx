"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/api";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<void>;
  busy: boolean;
  error: string | null;
  collapsed: boolean;
  onToggle: () => void;
}

function Actions({ actions }: { actions: Record<string, unknown> }) {
  const trades = (actions.trades as { message: string }[]) ?? [];
  const changes = (actions.watchlist_changes as { ticker: string; action: string }[]) ?? [];
  const errors = (actions.errors as string[]) ?? [];
  if (trades.length === 0 && changes.length === 0 && errors.length === 0) return null;
  return (
    <div className="mt-1 space-y-0.5">
      {trades.map((t, i) => (
        <div key={`t${i}`} className="text-xs text-up">
          ✓ {t.message}
        </div>
      ))}
      {changes.map((c, i) => (
        <div key={`c${i}`} className="text-xs text-finally-blue">
          ✓ Watchlist {c.action} {c.ticker}
        </div>
      ))}
      {errors.map((e, i) => (
        <div key={`e${i}`} className="text-xs text-down">
          ⚠ {e}
        </div>
      ))}
    </div>
  );
}

export function ChatPanel({
  messages,
  onSend,
  busy,
  error,
  collapsed,
  onToggle,
}: ChatPanelProps) {
  const [text, setText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, busy]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const msg = text.trim();
    if (!msg || busy) return;
    setText("");
    await onSend(msg);
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-bg-panel">
      <button
        onClick={onToggle}
        className="flex items-center justify-between border-b border-gray-800 px-3 py-2 text-left"
      >
        <span className="text-sm font-semibold text-gray-200">
          Assistant <span className="text-finally-purple">●</span>
        </span>
        <span className="text-xs text-gray-500">{collapsed ? "Expand ▸" : "Collapse ▾"}</span>
      </button>
      {!collapsed && (
        <>
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-3" data-testid="chat-log">
            {messages.length === 0 && (
              <p className="text-xs text-gray-500">
                Ask me to analyze your book, buy/sell, or manage the watchlist.
                Try: “buy 2 NVDA and add SNOW”.
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
                <div
                  className={`inline-block max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-finally-blue/20 text-gray-100"
                      : "bg-white/5 text-gray-200"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.content}</div>
                  {m.role === "assistant" && m.actions && <Actions actions={m.actions} />}
                </div>
              </div>
            ))}
            {busy && (
              <div className="text-left" data-testid="chat-loading">
                <span className="inline-block rounded-lg bg-white/5 px-3 py-2 text-sm text-gray-400">
                  Thinking…
                </span>
              </div>
            )}
            {error && <div className="text-xs text-down">⚠ {error}</div>}
          </div>
          <form onSubmit={submit} className="flex gap-2 border-t border-gray-800 p-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Message FinAlly…"
              aria-label="Chat message"
              disabled={busy}
              className="w-full rounded border border-gray-700 bg-bg px-2 py-1.5 text-sm text-gray-100 outline-none focus:border-finally-purple disabled:opacity-50"
              data-testid="chat-input"
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded bg-finally-purple px-4 py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
              data-testid="chat-send"
            >
              Send
            </button>
          </form>
        </>
      )}
    </div>
  );
}
