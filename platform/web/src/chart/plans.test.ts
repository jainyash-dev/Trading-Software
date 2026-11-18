import { describe, expect, it } from "vitest";
import { planOverlayFromRecords } from "./plans";

const scope = { symbol: "SYN", scanKey: "scan-1" };
const approved = {
  plan_id: "plan-abcdef123456",
  symbol: "SYN",
  scan_key: "scan-1",
  state: "APPROVED",
  entry_id: 1,
  journal_state: "PLANNED",
  journal_sync: "IN_SYNC",
  selected: { entry: 101.5, stop: 97.25, target: 120, quantity: 10 },
};

describe("FR-4.9 plan overlay", () => {
  it("draws entry, stop and target from the recorded plan only, labelled PLAN", () => {
    const overlay = planOverlayFromRecords([approved], scope);
    expect(overlay.lines.map((line) => [line.kind, line.price])).toEqual([
      ["entry", 101.5],
      ["stop", 97.25],
      ["target", 120],
    ]);
    expect(overlay.lines.every((line) => line.label.startsWith("PLAN "))).toBe(true);
    expect(overlay.notes).toEqual([]);
  });

  it("never draws cancelled, rejected or expired plans as active", () => {
    for (const state of ["CANCELLED", "REJECTED", "EXPIRED"]) {
      const overlay = planOverlayFromRecords([{ ...approved, state }], scope);
      expect(overlay.lines).toEqual([]);
      expect(overlay.notes[0]?.reason).toContain("Inactive");
    }
  });

  it("withholds lines when the journal is cancelled, closed, or unconfirmed (P4-IR-04)", () => {
    expect(planOverlayFromRecords([{ ...approved, journal_state: "CANCELLED", journal_sync: "CONFLICT" }], scope).lines).toEqual([]);
    expect(planOverlayFromRecords([{ ...approved, journal_state: "CLOSED" }], scope).lines).toEqual([]);
    const unknown = planOverlayFromRecords([{ ...approved, journal_state: null, journal_sync: "JOURNAL_UNAVAILABLE" }], scope);
    expect(unknown.lines).toEqual([]);
    expect(unknown.notes[0]?.reason).toContain("not confirmed");
    expect(planOverlayFromRecords([{ ...approved, journal_state: "OPEN" }], scope).lines).toHaveLength(3);
  });

  it("does not invent levels for drafts or missing values", () => {
    const draft = planOverlayFromRecords([{ ...approved, state: "DRAFT", selected: null, entry_id: null }], scope);
    expect(draft.lines).toEqual([]);
    expect(draft.notes[0]?.reason).toContain("No buffer is selected");
    const partial = planOverlayFromRecords([{ ...approved, selected: { entry: 101, stop: "", target: -5 } }], scope);
    expect(partial.lines.map((line) => line.kind)).toEqual(["entry"]);
    expect(partial.notes[0]?.reason).toContain("stop, target");
  });

  it("ignores plans for another symbol or another scan", () => {
    const other = planOverlayFromRecords(
      [
        { ...approved, symbol: "OTHER" },
        { ...approved, plan_id: "plan-2", scan_key: "scan-2" },
      ],
      scope,
    );
    expect(other.lines).toEqual([]);
    expect(other.notes).toHaveLength(2);
  });

  it("withholds lines when the journal recorded ZONE_INVALIDATED (review finding 4)", () => {
    const overlay = planOverlayFromRecords([{ ...approved, journal_zone_invalidated: true }], scope);
    expect(overlay.lines).toEqual([]);
    expect(overlay.notes[0]?.reason).toContain("ZONE_INVALIDATED");
  });

  it("withholds lines on a journal identity mismatch (review finding 1)", () => {
    expect(planOverlayFromRecords([{ ...approved, journal_state: null, journal_sync: "JOURNAL_IDENTITY_MISMATCH" }], scope).lines).toEqual([]);
  });
});
