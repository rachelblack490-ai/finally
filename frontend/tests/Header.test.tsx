import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Header } from "@/components/Header";
import type { Portfolio } from "@/lib/api";

const portfolio: Portfolio = {
  cash: 9000,
  positions_value: 1000,
  total_value: 10000,
  unrealized_pl: 25,
  positions: [],
};

describe("Header", () => {
  it("shows total value and cash", () => {
    render(<Header portfolio={portfolio} status="connected" />);
    expect(screen.getByText("$10,000.00")).toBeInTheDocument();
    expect(screen.getByText("$9,000.00")).toBeInTheDocument();
  });

  it("shows a Live status label when connected", () => {
    render(<Header portfolio={portfolio} status="connected" />);
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByTestId("status-dot")).toBeInTheDocument();
  });

  it("shows Reconnecting when the stream drops", () => {
    render(<Header portfolio={portfolio} status="reconnecting" />);
    expect(screen.getByText("Reconnecting")).toBeInTheDocument();
  });
});
