import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Sparkline } from "@/components/Sparkline";

describe("Sparkline", () => {
  it("renders a polyline when there are >= 2 values", () => {
    const { container } = render(<Sparkline values={[1, 2, 3, 2, 4]} />);
    const poly = container.querySelector("polyline");
    expect(poly).not.toBeNull();
    expect(poly?.getAttribute("points")?.split(" ").length).toBe(5);
  });

  it("renders no polyline for fewer than 2 values", () => {
    const { container } = render(<Sparkline values={[1]} />);
    expect(container.querySelector("polyline")).toBeNull();
  });

  it("uses green stroke when rising, red when falling", () => {
    const up = render(<Sparkline values={[1, 5]} />);
    expect(up.container.querySelector("polyline")?.getAttribute("stroke")).toBe("#16c784");
    const down = render(<Sparkline values={[5, 1]} />);
    expect(down.container.querySelector("polyline")?.getAttribute("stroke")).toBe("#ea3943");
  });
});
