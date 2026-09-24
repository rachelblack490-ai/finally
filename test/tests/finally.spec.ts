import { expect, test } from "@playwright/test";

const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  // Wait for the live stream to populate the first watchlist price.
  await expect(page.getByTestId("wl-price-AAPL")).not.toHaveText("—", {
    timeout: 15_000,
  });
});

test("fresh start: default watchlist, $10k, moving prices", async ({ page }) => {
  await expect(page.getByText("FinAlly")).toBeVisible();
  for (const t of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`wl-row-${t}`)).toBeVisible();
  }
  // Total value starts at ~$10,000.
  await expect(page.getByText("$10,000.00").first()).toBeVisible();
  // Status dot should reach "Live".
  await expect(page.getByText("Live")).toBeVisible();

  // Prices move: capture AAPL price, then expect it to change within a few seconds.
  const priceLocator = page.getByTestId("wl-price-AAPL");
  const first = await priceLocator.textContent();
  await expect
    .poll(async () => priceLocator.textContent(), { timeout: 10_000, intervals: [250] })
    .not.toBe(first);
});

test("add and remove a watchlist ticker", async ({ page }) => {
  await page.getByLabel("Add ticker").fill("SNOW");
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.getByTestId("wl-row-SNOW")).toBeVisible({ timeout: 10_000 });

  // Remove it via the row's × button.
  await page.getByTestId("wl-row-SNOW").hover();
  await page.getByLabel("Remove SNOW").click();
  await expect(page.getByTestId("wl-row-SNOW")).toHaveCount(0, { timeout: 10_000 });
});

test("buy and sell update cash and positions", async ({ page }) => {
  await page.getByLabel("Trade ticker").fill("AAPL");
  await page.getByLabel("Trade quantity").fill("5");
  await page.getByTestId("buy-btn").click();

  await expect(page.getByTestId("toast")).toContainText("Buy 5 AAPL", { timeout: 10_000 });
  await expect(page.getByTestId("pos-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("pos-row-AAPL")).toContainText("5.0000");

  // Sell 2 → quantity drops to 3.
  await page.getByLabel("Trade ticker").fill("AAPL");
  await page.getByLabel("Trade quantity").fill("2");
  await page.getByTestId("sell-btn").click();
  await expect(page.getByTestId("toast")).toContainText("Sell 2 AAPL", { timeout: 10_000 });
  await expect(page.getByTestId("pos-row-AAPL")).toContainText("3.0000");
});

test("heatmap and P&L chart render after a trade", async ({ page }) => {
  await page.getByLabel("Trade ticker").fill("NVDA");
  await page.getByLabel("Trade quantity").fill("2");
  await page.getByTestId("buy-btn").click();
  await expect(page.getByTestId("pos-row-NVDA")).toBeVisible({ timeout: 10_000 });

  // Heatmap renders an SVG tile with the ticker label.
  await expect(page.locator("svg text", { hasText: "NVDA" }).first()).toBeVisible({
    timeout: 10_000,
  });
  // P&L area chart renders a path (snapshots exist on start + after trades).
  await expect(page.locator(".recharts-area-area").first()).toBeVisible({ timeout: 10_000 });
});

test("mock chat replies and executes an inline trade", async ({ page }) => {
  const input = page.getByTestId("chat-input");
  await input.fill("buy 1 AAPL and add PLTR to watchlist");
  await page.getByTestId("chat-send").click();

  // Assistant reply (mock) appears.
  await expect(page.getByTestId("chat-log")).toContainText("[mock]", { timeout: 15_000 });
  // Inline trade confirmation.
  await expect(page.getByText(/✓ Buy 1 AAPL/)).toBeVisible({ timeout: 10_000 });
  // Position and watchlist reflect the actions.
  await expect(page.getByTestId("pos-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("wl-row-PLTR")).toBeVisible({ timeout: 10_000 });
});

test("SSE reconnects and keeps streaming after a reload", async ({ page }) => {
  // Reload drops the EventSource; the client should reconnect and resume ticks.
  await page.reload();
  await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
  const priceLocator = page.getByTestId("wl-price-MSFT");
  const first = await priceLocator.textContent();
  await expect
    .poll(async () => priceLocator.textContent(), { timeout: 10_000, intervals: [250] })
    .not.toBe(first);
});
