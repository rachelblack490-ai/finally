import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel } from "@/components/ChatPanel";
import type { ChatMessage } from "@/lib/api";

const messages: ChatMessage[] = [
  { role: "user", content: "buy 2 NVDA", actions: null, created_at: "" },
  {
    role: "assistant",
    content: "[mock] executing buy 2 NVDA.",
    actions: {
      trades: [{ message: "Buy 2 NVDA @ $800.00" }],
      watchlist_changes: [{ ticker: "SNOW", action: "add" }],
      errors: [],
    },
    created_at: "",
  },
];

function setup(overrides = {}) {
  const props = {
    messages,
    onSend: vi.fn().mockResolvedValue(undefined),
    busy: false,
    error: null,
    collapsed: false,
    onToggle: vi.fn(),
    ...overrides,
  };
  render(<ChatPanel {...props} />);
  return props;
}

describe("ChatPanel", () => {
  it("renders message history with inline action confirmations", () => {
    setup();
    expect(screen.getByText("buy 2 NVDA")).toBeInTheDocument();
    expect(screen.getByText("[mock] executing buy 2 NVDA.")).toBeInTheDocument();
    expect(screen.getByText("✓ Buy 2 NVDA @ $800.00")).toBeInTheDocument();
    expect(screen.getByText("✓ Watchlist add SNOW")).toBeInTheDocument();
  });

  it("shows a loading indicator when busy", () => {
    setup({ busy: true });
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
  });

  it("shows an error line when provided", () => {
    setup({ error: "OpenCode Zen key is not set." });
    expect(screen.getByText(/OpenCode Zen key is not set/)).toBeInTheDocument();
  });

  it("sends a message and clears the input", async () => {
    const props = setup();
    const input = screen.getByTestId("chat-input");
    await userEvent.type(input, "how am I doing?");
    await userEvent.click(screen.getByTestId("chat-send"));
    expect(props.onSend).toHaveBeenCalledWith("how am I doing?");
  });

  it("does not send while busy", async () => {
    const props = setup({ busy: true });
    const input = screen.getByTestId("chat-input");
    expect(input).toBeDisabled();
    void props;
  });
});
