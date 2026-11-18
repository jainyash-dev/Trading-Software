import { describe, expect, it } from "vitest";
import { prepareSeries } from "./model";
import { zonesFromStored } from "./zones";

describe("prepareSeries volume honesty", () => {
  it("accepts null volume and rejects negative volume", () => {
    const ok = prepareSeries([
      { time: "2024-01-02", open: 1, high: 2, low: 1, close: 1.5, volume: null },
      { time: "2024-01-03", open: 1.5, high: 2.5, low: 1.4, close: 2, volume: 0 },
    ]);
    expect(ok.ok).toBe(true);
    const bad = prepareSeries([{ time: "2024-01-02", open: 1, high: 2, low: 1, close: 1.5, volume: -1 }]);
    expect(bad.ok).toBe(false);
  });
});

describe("zonesFromStored", () => {
  it("maps candidates, fresh, and blocked rows without inventing freshness", () => {
    const zones = zonesFromStored(
      {
        candidates: [
          {
            execution_tf: "D",
            zone: {
              zone_id: "d1",
              side: "demand",
              proximal: 10,
              distal: 9,
              overlay_status: "FRESH",
              created_time: "2024-01-02",
            },
          },
        ],
        fresh_zones: [
          {
            tf: "W",
            zone_id: "w1",
            side: "demand",
            proximal: 8,
            distal: 7,
            overlay_status: "FRESH",
            created_time: "2024-01-01",
          },
        ],
        blocked_zones: [
          {
            tf: "M",
            zone_id: "m1",
            side: "supply",
            proximal: 20,
            distal: 21,
            overlay_status: "TESTED",
            disposition: "BLOCKED_BY_OVERLAY",
            created_time: "2023-12-01",
          },
        ],
      },
      "INFY",
      { M: true, W: true, D: true },
    );
    expect(zones.map((zone) => zone.engineId).sort()).toEqual(["d1", "m1", "w1"]);
    expect(zones.find((zone) => zone.engineId === "d1")?.overlayStatus).toBe("FRESH");
    expect(zones.find((zone) => zone.engineId === "m1")?.overlayStatus).toBe("TESTED");
    expect(zones.find((zone) => zone.engineId === "m1")?.disposition).toBe("BLOCKED_BY_OVERLAY");
    expect(zones.find((zone) => zone.engineId === "m1")?.label).toContain("TESTED");
  });

  it("maps unknown overlay codes to UNKNOWN and never to FRESH", () => {
    const zones = zonesFromStored(
      {
        candidates: [
          {
            execution_tf: "D",
            zone: {
              zone_id: "x1",
              side: "demand",
              proximal: 1,
              distal: 0.5,
              overlay_status: "WEIRD_STATUS",
            },
          },
        ],
        fresh_zones: [
          {
            tf: "D",
            zone_id: "x2",
            side: "demand",
            proximal: 2,
            distal: 1,
          },
        ],
      },
      "INFY",
    );
    expect(zones.find((zone) => zone.engineId === "x1")?.overlayStatus).toBe("UNKNOWN");
    // D3 list contract: fresh_zones without an explicit status field still render as FRESH.
    expect(zones.find((zone) => zone.engineId === "x2")?.overlayStatus).toBe("FRESH");
  });

  it("respects timeframe visibility toggles", () => {
    const zones = zonesFromStored(
      {
        fresh_zones: [
          { tf: "D", zone_id: "d1", side: "demand", proximal: 1, distal: 0.5, overlay_status: "FRESH" },
          { tf: "W", zone_id: "w1", side: "demand", proximal: 1, distal: 0.5, overlay_status: "FRESH" },
        ],
      },
      "INFY",
      { M: false, W: false, D: true },
    );
    expect(zones).toHaveLength(1);
    expect(zones[0]?.engineId).toBe("d1");
  });
});
