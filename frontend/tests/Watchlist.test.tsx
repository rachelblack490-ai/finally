import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Watchlist } from "@/components/Watchlist";
import type { PriceMap, WatchlistItem } from "@/lib/api";

const items: WatchlistItem[] = [
  { ticker: "AAPL", price: 190, previous_price: 189, change: 1, change_percent: 0.5, direction: "up" },
  { ticker: "TSLA", price: 250, previous_price: 251, change: -1, change_percent: -0.4, direction: "down" },
];

const prices: PriceMap = {
  AAPL: { ticker: "AAPL", price: 191, previous_price: 190, timestamp: 0, change: 1, change_percent: 0.5, direction: "up" },
  TSLA: { ticker: "TSLA", price: 249, previous_price: 250, timestamp: 0, change: -1, change_percent: -0.4, direction: "down" },
};

function setup(overrides = {}) {
  const props = {
    items,
    prices,
    sessionOpen: { AAPL: 190, TSLA: 250 },
    histories: { AAPL: [190, 190.5, 191], TSLA: [250, 249.5, 249] },
    selected: "AAPL",
    onSelect: vi.fn(),
    onRemove: vi.fn(),
    onAdd: vi.fn(),
    ...overrides,
  };
  render(<Watchlist {...props} />);
  return props;
}

describe("Watchlist", () => {
  it("renders rows with live prices", () => {
    setup();
    expect(screen.getByTestId("wl-price-AAPL")).toHaveTextContent("191.00");
    expect(screen.getByTestId("wl-price-TSLA")).toHaveTextContent("249.00");
  });

  it("applies a flash class based on tick direction", () => {
    setup();
    expect(screen.getByTestId("wl-price-AAPL").className).toContain("animate-flashUp");
    expect(screen.getByTestId("wl-price-TSLA").className).toContain("animate-flashDown");
  });

  it("computes session change % from the session open", () => {
    setup();
    // AAPL: 191 vs open 190 => +0.53%
    expect(screen.getByTestId("wl-row-AAPL")).toHaveTextContent("+0.53%");
  });

  it("selects a ticker on row click", async () => {
    const props = setup();
    await userEvent.click(screen.getByTestId("wl-row-TSLA"));
    expect(props.onSelect).toHaveBeenCalledWith("TSLA");
  });

  it("removes a ticker via the × button", async () => {
    const props = setup();
    await userEvent.click(screen.getByLabelText("Remove TSLA"));
    expect(props.onRemove).toHaveBeenCalledWith("TSLA");
  });

  it("adds a ticker via the form", async () => {
    const props = setup();
    await userEvent.type(screen.getByLabelText("Add ticker"), "snow");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(props.onAdd).toHaveBeenCalledWith("SNOW");
  });
});
