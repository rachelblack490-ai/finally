import { describe, expect, it } from "vitest";
import { fmtMoney, fmtNum, fmtPct, sessionChangePct } from "@/lib/format";

describe("format helpers", () => {
  it("formats money with currency", () => {
    expect(fmtMoney(10000)).toBe("$10,000.00");
    expect(fmtMoney(1234.5)).toBe("$1,234.50");
  });

  it("renders em dash for null", () => {
    expect(fmtMoney(null)).toBe("—");
    expect(fmtPct(undefined)).toBe("—");
    expect(fmtNum(NaN)).toBe("—");
  });

  it("adds sign to percentages", () => {
    expect(fmtPct(1.2)).toBe("+1.20%");
    expect(fmtPct(-3)).toBe("-3.00%");
    expect(fmtPct(0)).toBe("0.00%");
  });

  it("computes session change percent vs open", () => {
    expect(sessionChangePct(110, 100)).toBeCloseTo(10);
    expect(sessionChangePct(90, 100)).toBeCloseTo(-10);
    expect(sessionChangePct(100, 0)).toBe(0);
  });
});
