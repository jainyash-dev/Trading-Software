import { describe, expect, it } from "vitest";
import {
  ACTIONABLE_STATUS,
  candidateStatusOf,
  symbolStatusOf,
  scanOutcome,
  applyConfigParameters,
  filterSymbols,
  forbiddenParameterPaths,
  isTerminalJob,
  progressLabel,
  scanRequestBody,
  type ScanDraft,
} from "./model";
import type { ResearchSymbol } from "../../types/contracts";

const draft: ScanDraft = {
  mode: "MANUAL",
  tradeType: "MIT",
  universeMode: "SUPPORTED",
  symbols: [],
  asOf: "2024-06-14",
  datasetId: "local-dataset",
  risk: null,
};

describe("scanner presentation", () => {
  it("does not turn job progress into a percentage", () => {
    expect(progressLabel({ done: 1, total: 4, unit: "symbols" })).toBe("1 of 4 symbols");
    expect(progressLabel({ done: 1, unit: "symbols" })).toBe("1 symbols");
    expect(progressLabel(null)).toBeNull();
    expect(progressLabel({ done: 1, total: 4, unit: "symbols" })).not.toContain("%");
  });

  it("recognises terminal job states without treating partial as complete", () => {
    expect(isTerminalJob("RUNNING")).toBe(false);
    expect(isTerminalJob("SUCCEEDED_PARTIAL")).toBe(true);
    expect(isTerminalJob("INTERRUPTED")).toBe(true);
    expect(isTerminalJob("CANCELLED")).toBe(true);
  });

  it("does not apply max_base_candles from a saved configuration", () => {
    const applied = applyConfigParameters(draft, {
      trade_type: "WIT-75",
      max_base_candles: 3,
      Rules: { max_base_candles: 2 },
    });
    expect(applied.draft.tradeType).toBe("WIT-75");
    expect(applied.ignored).toEqual(expect.arrayContaining(["max_base_candles", "Rules.max_base_candles", "Rules"]));
    expect(forbiddenParameterPaths({ nested: { max_base_candles: 1 } })).toEqual(["nested.max_base_candles"]);
    const body = scanRequestBody(applied.draft);
    expect(body.ok).toBe(true);
    if (body.ok) expect(body.body).not.toHaveProperty("max_base_candles");
  });

  it("filters without reordering or rewriting a status", () => {
    const symbols: ResearchSymbol[] = [
      { symbol: "AAA", symbol_status: "DATA_INSUFFICIENT", limitations: ["UNIVERSE_UNVERIFIED"] },
      { symbol: "BBB", symbol_status: "BLOCKED", reasons: ["M4B_INTRADAY_NOT_APPROVED"] },
      {
        symbol: "CCC",
        symbol_status: "EVALUATED",
        candidates: [{ candidate_status: "MANUAL_REVIEW", zone: { tf: "D", overlay_status: "FRESH" }, gates: [{ outcome: "MANUAL" }] }],
      },
    ];
    const filtered = filterSymbols(symbols, { symbol: "", status: "BLOCKED", timeframe: "", quality: "" });
    expect(filtered.map((row) => row.symbol)).toEqual(["BBB"]);
    expect(filtered[0]?.symbol_status).toBe("BLOCKED");
    const ordered = filterSymbols(symbols, { symbol: "", status: "", timeframe: "D", quality: "" });
    expect(ordered.map((row) => row.symbol)).toEqual(["CCC"]);
    expect(symbols.map((row) => row.symbol)).toEqual(["AAA", "BBB", "CCC"]);
  });
});

describe("scan outcome explanation (FR-3.4 / OI-002)", () => {
  const sym = (symbol: string, symbol_status: string, extra: Record<string, unknown> = {}) => ({ symbol, symbol_status, ...extra });
  const base = { completeness: "COMPLETE", dataset_id: "ds-1", symbols_not_opened: [] as string[] };
  const call = (envelope: Record<string, unknown> | null, extra: Partial<Parameters<typeof scanOutcome>[0]> = {}) =>
    scanOutcome({ envelope, connected: true, error: null, currentDatasetIds: ["ds-1"], ...extra });

  it("a failed scan is never a zero-candidate success", () => {
    expect(call({ ...base, completeness: "FAILED", symbols: [] })?.kind).toBe("FAILED");
  });

  it("an unavailable scanner is not a zero-candidate result", () => {
    const outcome = call(null, { connected: false });
    expect(outcome?.kind).toBe("UNAVAILABLE");
    expect(outcome?.headline).toContain("not a scan with zero candidates");
    expect(call(null, { error: { code: "INTERNAL", message: "x" } })?.kind).toBe("UNAVAILABLE");
    expect(call(null, { error: { code: "NOT_FOUND", message: "x" } })).toBeNull();
  });

  it("explains nothing qualified from stored statuses and deciding gates only", () => {
    const outcome = call({
      ...base,
      symbols: [
        sym("A", "NO_FRESH_EXECUTION_ZONE", { blocked_zones: [{}, {}] }),
        sym("B", "DATA_INSUFFICIENT", { reasons: ["NO_BARS"] }),
        sym("C", "EVALUATED", {
          candidates: [
            { candidate_status: "REJECTED", deciding_gates: [{ status: "REJECTED", gates: [{ gate: "G2", outcome: "FAIL" }] }] },
            { candidate_status: "MANUAL_REVIEW", deciding_gates: [{ status: "MANUAL_REVIEW", gates: [{ gate: "G5", outcome: "MANUAL" }] }] },
          ],
        }),
      ],
    });
    expect(outcome?.kind).toBe("NOTHING_QUALIFIED");
    const codes = outcome?.lines.map((line) => line.code);
    expect(codes).toEqual(expect.arrayContaining(["NO_FRESH_ZONE", "ZONES_BLOCKED", "EVIDENCE_MISSING", "CANDIDATES_REJECTED", "EVIDENCE_INCOMPLETE"]));
    expect(outcome?.lines.find((line) => line.code === "CANDIDATES_REJECTED")?.text).toContain("G2 FAIL");
    expect(outcome?.lines.find((line) => line.code === "EVIDENCE_MISSING")?.text).toContain("NO_BARS");
  });

  it("partial and stale scans are disclosed; unknown outcome is not zero", () => {
    const outcome = call(
      { ...base, completeness: "PARTIAL", dataset_id: "ds-0", symbols_not_opened: ["X", "Y"], symbols: [sym("A", "NO_FRESH_EXECUTION_ZONE")] },
    );
    expect(outcome?.headline).toContain("partial");
    const codes = outcome?.lines.map((line) => line.code);
    expect(codes).toEqual(expect.arrayContaining(["PARTIAL_SCAN", "STALE_DATASET"]));
    expect(outcome?.lines.find((line) => line.code === "PARTIAL_SCAN")?.text).toContain("unknown, not zero");
    // Unknown current dataset list: staleness is not claimed.
    expect(call({ ...base, dataset_id: "ds-0", symbols: [] }, { currentDatasetIds: null })?.lines.map((line) => line.code)).not.toContain("STALE_DATASET");
  });

  it("an empty stored scan is EMPTY; qualified candidates keep manual checks pending", () => {
    expect(call({ ...base, symbols: [] })?.kind).toBe("EMPTY");
    expect(call({ ...base, completeness: "PARTIAL", symbols: [], symbols_not_opened: ["A"] })?.headline).toContain("not a zero-candidate result");
    const qualified = call({ ...base, symbols: [sym("A", "EVALUATED", { candidates: [{ candidate_status: ACTIONABLE_STATUS, deciding_gates: [] }] })] });
    expect(qualified?.kind).toBe("QUALIFIED");
    expect(qualified?.headline).toContain("Manual checks are still pending");
  });

  it("stored counts that disagree with rows are flagged, not reconciled silently", () => {
    const outcome = call({
      ...base,
      counts: { candidate_status: { [ACTIONABLE_STATUS]: 2 } },
      symbols: [sym("A", "EVALUATED", { candidates: [{ candidate_status: "REJECTED" }] })],
    });
    expect(outcome?.lines.map((line) => line.code)).toContain("COUNTS_DISAGREE");
    expect(outcome?.lines.find((line) => line.code === "CANDIDATES_REJECTED")?.text).toContain("not stored in this envelope");
  });
});

describe("canonical stored status keys (FR-3.3 regression)", () => {
  // nse/research reports emit `status` on symbol and candidate rows; there is no symbol_status/candidate_status.
  const canonical = {
    completeness: "COMPLETE",
    dataset_id: "ds-1",
    symbols_not_opened: [],
    symbols: [{ symbol: "SYN", status: "EVALUATED", candidates: [{ status: ACTIONABLE_STATUS }] }],
  };

  it("reads `status` for symbols and candidates", () => {
    expect(symbolStatusOf(canonical.symbols[0])).toBe("EVALUATED");
    expect(candidateStatusOf(canonical.symbols[0]!.candidates[0])).toBe(ACTIONABLE_STATUS);
    expect(candidateStatusOf({ candidate_status: "REJECTED" })).toBe("REJECTED");
    expect(candidateStatusOf({})).toBeUndefined();
  });

  it("a canonical envelope with an actionable candidate is QUALIFIED, not NOTHING_QUALIFIED", () => {
    const outcome = scanOutcome({ envelope: canonical, connected: true, error: null, currentDatasetIds: ["ds-1"] });
    expect(outcome?.kind).toBe("QUALIFIED");
    expect(outcome?.lines.map((line) => line.code)).not.toContain("STATUS_UNAVAILABLE");
  });

  it("the decision-status filter matches canonical rows", () => {
    expect(filterSymbols(canonical.symbols as never, { symbol: "", status: ACTIONABLE_STATUS, timeframe: "", quality: "" })).toHaveLength(1);
    expect(filterSymbols(canonical.symbols as never, { symbol: "", status: "REJECTED", timeframe: "", quality: "" })).toHaveLength(0);
  });
});
