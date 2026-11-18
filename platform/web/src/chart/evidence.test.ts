import { describe, expect, it } from "vitest";
import { analysisEvidence, type EvidenceInput } from "./evidence";
import type { CandlePayload, SymbolBundle } from "../types/contracts";

const candles: CandlePayload = {
  symbol: "SYN",
  dataset_id: "ds-1",
  candles: [],
  limitations: [],
  missing_sessions: [],
  invalid_candles: [],
  volume_state: "PRESENT",
  volume_source: "CSV_VOLUME",
  data_quality: { fixture: true, certified: false },
};
const bundle: SymbolBundle = {
  scan_key: "scan-1",
  dataset_id: "ds-1",
  as_of: "2024-06-07",
  completeness: "COMPLETE",
  stored: { symbol: "SYN", status: "EVALUATED", candidates: [] } as unknown as SymbolBundle["stored"],
};

function base(overrides: Partial<EvidenceInput> = {}): EvidenceInput {
  return {
    symbol: "SYN",
    datasetId: "ds-1",
    candles: { ok: true, data: candles, fixture: true },
    bundle: { ok: true, data: bundle, fixture: true },
    explain: { ok: true, data: {} },
    plans: { ok: true, data: {} },
    series: { ok: true, count: 20 },
    ...overrides,
  };
}

function state(rows: ReturnType<typeof analysisEvidence>, source: string) {
  return rows.find((row) => row.source === source)?.state;
}

describe("analysis evidence status", () => {
  it("valid stored bundle and candles are AVAILABLE and fixture is labelled", () => {
    const rows = analysisEvidence(base());
    expect(state(rows, "Candles")).toBe("AVAILABLE");
    expect(state(rows, "Stored bundle")).toBe("AVAILABLE");
    expect(state(rows, "Volume")).toBe("AVAILABLE");
    expect(state(rows, "Data certification")).toBe("FIXTURE");
  });

  it("a missing bundle is MISSING and qualification is UNAVAILABLE, not a negative finding", () => {
    const rows = analysisEvidence(base({ bundle: { ok: false, status: 404, code: "NOT_FOUND", message: "Symbol is not in the stored scan" } }));
    expect(state(rows, "Stored bundle")).toBe("MISSING");
    const qualification = rows.find((row) => row.source === "Qualification");
    expect(qualification?.state).toBe("UNAVAILABLE");
    expect(qualification?.detail).toContain("not failed and not passed");
  });

  it("wrong session or wrong data version is STALE", () => {
    expect(state(analysisEvidence(base({ bundle: { ok: false, status: 409, code: "CONFLICT", message: "as_of does not match the stored scan" } })), "Stored bundle")).toBe("STALE");
    expect(state(analysisEvidence(base({ candles: { ok: false, status: 409, code: "CONFLICT", message: "dataset_id does not match the local files" } })), "Candles")).toBe("STALE");
    expect(state(analysisEvidence(base({ bundle: { ok: true, data: { ...bundle, dataset_id: "ds-0" } } })), "Stored bundle")).toBe("STALE");
  });

  it("wrong symbol is FAILED and never drawn as the requested symbol", () => {
    expect(state(analysisEvidence(base({ candles: { ok: true, data: { ...candles, symbol: "OTHER" } } })), "Candles")).toBe("FAILED");
    const wrong = { ...bundle, stored: { symbol: "OTHER", candidates: [] } as unknown as SymbolBundle["stored"] };
    expect(state(analysisEvidence(base({ bundle: { ok: true, data: wrong } })), "Stored bundle")).toBe("FAILED");
  });

  it("partial scans and gaps are INCOMPLETE; no candles is MISSING; invalid series FAILED", () => {
    expect(state(analysisEvidence(base({ bundle: { ok: true, data: { ...bundle, completeness: "PARTIAL" } } })), "Stored bundle")).toBe("INCOMPLETE");
    expect(state(analysisEvidence(base({ candles: { ok: true, data: { ...candles, missing_sessions: ["2024-06-05"] } } })), "Candles")).toBe("INCOMPLETE");
    expect(state(analysisEvidence(base({ series: { ok: true, count: 0 } })), "Candles")).toBe("MISSING");
    expect(state(analysisEvidence(base({ series: { ok: false, count: 3 } })), "Candles")).toBe("FAILED");
  });

  it("unavailable data and disconnection are distinct from each other", () => {
    expect(state(analysisEvidence(base({ candles: { ok: false, status: 422, code: "DATA_INSUFFICIENT", message: "No accepted local market data" } })), "Candles")).toBe("UNAVAILABLE");
    expect(state(analysisEvidence(base({ candles: { ok: false, status: 0, code: "DISCONNECTED", message: "x" } })), "Candles")).toBe("FAILED");
  });

  it("open gates make qualification INCOMPLETE; no candidate in a good bundle is the stored result", () => {
    const withGates = {
      ...bundle,
      stored: { symbol: "SYN", candidates: [{ gates: [{ gate: "G5", outcome: "MANUAL" }, { gate: "G1", outcome: "PASS" }] }] } as unknown as SymbolBundle["stored"],
    };
    const rows = analysisEvidence(base({ bundle: { ok: true, data: withGates } }));
    expect(state(rows, "Qualification")).toBe("INCOMPLETE");
    expect(rows.find((row) => row.source === "Qualification")?.detail).toContain("G5 MANUAL");
    expect(analysisEvidence(base()).find((row) => row.source === "Qualification")?.detail).toContain("recorded no candidate");
  });

  it("non-fixture data is UNCERTIFIED, never certified; volume partial/unsupported are not zero", () => {
    const rows = analysisEvidence(
      base({
        candles: { ok: true, data: { ...candles, data_quality: { fixture: false, certified: false }, volume_state: "UNSUPPORTED" }, fixture: false },
        bundle: { ok: true, data: bundle, fixture: false },
      }),
    );
    expect(state(rows, "Data certification")).toBe("UNCERTIFIED");
    expect(state(rows, "Volume")).toBe("UNAVAILABLE");
    expect(state(analysisEvidence(base({ candles: { ok: true, data: { ...candles, volume_state: "PARTIAL" } } })), "Volume")).toBe("INCOMPLETE");
  });

  it("review finding 2: a DATA_INSUFFICIENT or BLOCKED symbol is never an AVAILABLE negative result", () => {
    for (const status of ["DATA_INSUFFICIENT", "BLOCKED"]) {
      const data = { ...bundle, stored: { symbol: "SYN", status, candidates: [] } as unknown as SymbolBundle["stored"] };
      const row = analysisEvidence(base({ bundle: { ok: true, data } })).find((item) => item.source === "Qualification");
      expect(row?.state).not.toBe("AVAILABLE");
      expect(row?.detail).toContain(status);
    }
  });

  it("review finding 2: another symbol's or stale bundle's candidates are not summarised for this symbol", () => {
    const foreign = { ...bundle, stored: { symbol: "OTHER", status: "EVALUATED", candidates: [{ gates: [] }] } as unknown as SymbolBundle["stored"] };
    expect(state(analysisEvidence(base({ bundle: { ok: true, data: foreign } })), "Qualification")).toBe("UNAVAILABLE");
    expect(state(analysisEvidence(base({ bundle: { ok: true, data: { ...bundle, dataset_id: "ds-0" } } })), "Qualification")).toBe("UNAVAILABLE");
    const partial = { ...bundle, completeness: "PARTIAL", stored: { symbol: "SYN", status: "EVALUATED", candidates: [{ gates: [] }] } as unknown as SymbolBundle["stored"] };
    expect(state(analysisEvidence(base({ bundle: { ok: true, data: partial } })), "Qualification")).toBe("INCOMPLETE");
  });
});
