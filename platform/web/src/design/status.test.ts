import { describe, expect, it } from "vitest";
import { moveDrawing, prepareSeries, zoneStyle, createDrawing } from "../chart/model";
import { presentStatus } from "./status";
import type { ZoneView } from "../types/contracts";

describe("status language", () => {
  it("does not present an unknown code as pass", () => {
    const status = presentStatus("NOT_A_REAL_STATUS");
    expect(status.label).toBe("Unknown status: NOT_A_REAL_STATUS");
    expect(status.tone).not.toBe("ok");
    expect(status.label.toLowerCase()).not.toContain("pass");
  });

  it("keeps pass, fail, manual, and the owner limitation codes labelled", () => {
    expect(presentStatus("PASS").label).toBe("Pass");
    expect(presentStatus("FAIL").tone).toBe("fail");
    expect(presentStatus("MANUAL").tone).toBe("manual");
    expect(presentStatus("DATA_INSUFFICIENT").label).toBe("Data insufficient");
    expect(presentStatus("UNIVERSE_UNVERIFIED").label).toBe("Universe unverified");
    expect(presentStatus("ZONE_IDENTITY_UNRESOLVED").tone).not.toBe("ok");
    const missingZone = presentStatus("NO_FRESH_EXECUTION_ZONE");
    expect(missingZone.label).toBe("No fresh execution zone");
    expect(missingZone.tone).not.toBe("ok");
    expect(presentStatus("TESTED").tone).not.toBe("ok");
    expect(presentStatus("TESTED").label).not.toMatch(/fresh/i);
    expect(presentStatus("UNKNOWN").tone).toBe("unknown");
  });
});

describe("series and zones", () => {
  it("refuses duplicate timestamps instead of dropping them", () => {
    const prepared = prepareSeries([
      { time: "2024-01-02", open: 1, high: 2, low: 1, close: 1.5, volume: 10 },
      { time: "2024-01-02", open: 1, high: 2, low: 1, close: 1.5, volume: 10 },
    ]);
    expect(prepared.ok).toBe(false);
    if (!prepared.ok) {
      expect(prepared.candles).toHaveLength(2);
      expect(prepared.issues.some((issue) => issue.code === "DUPLICATE_TIMESTAMP")).toBe(true);
    }
  });

  it("does not style supply or unknown demand as fresh demand", () => {
    const demand = zoneStyle({ side: "demand", overlayStatus: "FRESH" });
    const unknown = zoneStyle({ side: "demand", overlayStatus: "UNKNOWN" });
    const supply = zoneStyle({ side: "supply", overlayStatus: "FRESH" });
    expect(demand.freshDemand).toBe(true);
    expect(unknown.freshDemand).toBe(false);
    expect(unknown.fill).not.toBe(demand.fill);
    expect(supply.freshDemand).toBe(false);
    expect(supply.fill).not.toBe(demand.fill);
  });

  it("moves a drawing without changing a zone", () => {
    const zone: ZoneView = {
      source: "engine",
      engineId: "z",
      symbol: "EXAMPLE",
      timeframe: "D",
      side: "demand",
      startTime: "2024-01-02",
      createdTime: "2024-01-03",
      proximal: 10,
      distal: 9,
      overlayStatus: "FRESH",
      label: "demand FRESH",
    };
    const drawing = createDrawing("horizontal", [{ time: "2024-01-02", price: 10 }], "", {
      symbol: "EXAMPLE",
      timeframe: "D",
    });
    const moved = moveDrawing(drawing, 1, null);
    expect(moved.points[0]?.price).toBe(11);
    expect(zone.proximal).toBe(10);
    expect(moved.persistence).toBe("MEMORY_ONLY");
    expect(zone.source).toBe("engine");
  });
});
