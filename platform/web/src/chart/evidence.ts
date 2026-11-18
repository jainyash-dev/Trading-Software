/**
 * P2-F / FR-4.7 / UX-013: evidence status beside the chart.
 *
 * Classifies what each API source actually returned. It never scores eligibility and never turns
 * unavailable evidence into a negative or positive finding. "No stored candidate" in an available
 * bundle is the stored scan's own result; a failed bundle request is UNAVAILABLE, not "no candidate".
 */

import type { CandlePayload, SymbolBundle } from "../types/contracts";

export type EvidenceState =
  | "AVAILABLE"
  | "MISSING"
  | "INCOMPLETE"
  | "STALE"
  | "UNAVAILABLE"
  | "FAILED"
  | "FIXTURE"
  | "UNCERTIFIED";

export interface EvidenceRow {
  source: "Candles" | "Stored bundle" | "Qualification" | "Explanation" | "Volume" | "Data certification" | "Plans";
  state: EvidenceState;
  detail: string;
}

export type Fetched<T> =
  | { ok: true; data: T; fixture?: boolean }
  | { ok: false; status: number; code: string; message: string };

export interface EvidenceInput {
  symbol: string;
  datasetId: string;
  candles: Fetched<CandlePayload> | null;
  bundle: Fetched<SymbolBundle> | null;
  explain: Fetched<unknown> | null;
  plans: Fetched<unknown> | null;
  series: { ok: boolean; count: number };
}

function failure(result: { status: number; code: string; message: string }, subject: string): Pick<EvidenceRow, "state" | "detail"> {
  if (result.status === 0) return { state: "FAILED", detail: `${subject}: local API not reachable.` };
  if (result.status === 404) return { state: "MISSING", detail: `${subject}: ${result.message}` };
  if (result.status === 409) return { state: "STALE", detail: `${subject} does not match this request (${result.message}).` };
  if (result.status === 422) return { state: "UNAVAILABLE", detail: `${subject}: ${result.message}` };
  return { state: "FAILED", detail: `${subject}: ${result.code} ${result.message}` };
}

const TRUNCATING = new Set(["SERIES_TRUNCATED", "INVALID_SOURCE_CANDLES_EXCLUDED", "NO_BARS", "NO_CANDLES_AT_OR_BEFORE_AS_OF"]);

export function analysisEvidence(input: EvidenceInput): EvidenceRow[] {
  const rows: EvidenceRow[] = [];
  const symbol = input.symbol.toUpperCase();
  const candles = input.candles;
  let fixture = false;
  if (candles === null) {
    rows.push({ source: "Candles", state: "UNAVAILABLE", detail: "Not requested yet." });
  } else if (!candles.ok) {
    rows.push({ source: "Candles", ...failure(candles, "Candle route") });
  } else {
    const data = candles.data;
    fixture = Boolean(candles.fixture || data.data_quality?.fixture);
    if (data.symbol && data.symbol.toUpperCase() !== symbol) {
      rows.push({ source: "Candles", state: "FAILED", detail: `Candle payload is for ${data.symbol}, not ${symbol}. Not drawn as ${symbol}.` });
    } else if (data.dataset_id && input.datasetId && data.dataset_id !== input.datasetId) {
      rows.push({ source: "Candles", state: "STALE", detail: `Candles are dataset ${data.dataset_id}; the scan used ${input.datasetId}.` });
    } else if (!input.series.ok) {
      rows.push({ source: "Candles", state: "FAILED", detail: "Series has invalid, duplicate, or out-of-order rows. Not drawn." });
    } else if (input.series.count === 0) {
      rows.push({ source: "Candles", state: "MISSING", detail: "No drawable candles at or before as_of. Nothing was filled." });
    } else {
      const partial =
        (data.missing_sessions?.length || 0) > 0 ||
        (data.invalid_candles?.length || 0) > 0 ||
        (data.limitations || []).some((code) => TRUNCATING.has(code));
      rows.push({
        source: "Candles",
        state: partial ? "INCOMPLETE" : "AVAILABLE",
        detail: partial
          ? `${input.series.count} candles; missing ${data.missing_sessions?.length || 0}, invalid ${data.invalid_candles?.length || 0}. Gaps not filled.`
          : `${input.series.count} candles from the candle route.`,
      });
    }
    const volume = data.volume_state;
    rows.push({
      source: "Volume",
      state: volume === "PRESENT" ? "AVAILABLE" : volume === "PARTIAL" ? "INCOMPLETE" : "UNAVAILABLE",
      detail:
        volume === "UNSUPPORTED"
          ? "Source has no volume column. Volume is not drawn and is not zero."
          : volume === "PRESENT"
            ? `Traded quantity (${data.volume_source || "source unknown"}).`
            : volume === "PARTIAL"
              ? "Some candles have no stated volume; those bars are omitted, not zero."
              : "No candle has a stated volume.",
    });
  }

  const bundle = input.bundle;
  if (bundle === null) {
    rows.push({ source: "Stored bundle", state: "UNAVAILABLE", detail: "Not requested yet." });
    rows.push({ source: "Qualification", state: "UNAVAILABLE", detail: "Stored bundle not loaded. This is not a finding." });
  } else if (!bundle.ok) {
    rows.push({ source: "Stored bundle", ...failure(bundle, "Stored scan bundle") });
    rows.push({ source: "Qualification", state: "UNAVAILABLE", detail: "Stored bundle unavailable. Qualification is unknown, not failed and not passed." });
  } else {
    const data = bundle.data;
    fixture = fixture || Boolean(bundle.fixture);
    const storedSymbol = String(data.stored?.symbol || "").toUpperCase();
    let bundleRow: EvidenceRow;
    if (storedSymbol && storedSymbol !== symbol) {
      bundleRow = { source: "Stored bundle", state: "FAILED", detail: `Bundle holds ${storedSymbol}, not ${symbol}.` };
    } else if (data.dataset_id && input.datasetId && data.dataset_id !== input.datasetId) {
      bundleRow = { source: "Stored bundle", state: "STALE", detail: `Bundle dataset ${data.dataset_id} differs from ${input.datasetId}.` };
    } else if (data.completeness && data.completeness !== "COMPLETE") {
      bundleRow = { source: "Stored bundle", state: "INCOMPLETE", detail: `Stored scan is ${data.completeness}. It is not a complete scan.` };
    } else if (!data.completeness) {
      bundleRow = { source: "Stored bundle", state: "INCOMPLETE", detail: "Stored scan does not state its completeness." };
    } else {
      bundleRow = { source: "Stored bundle", state: "AVAILABLE", detail: `Stored scan ${data.scan_key || ""} as of ${data.as_of || "unknown"}.` };
    }
    rows.push(bundleRow);
    const stored = (data.stored || {}) as Record<string, unknown>;
    const symbolStatus = String(stored.status || stored.symbol_status || "");
    const candidates = (data.stored?.candidates || []) as Array<Record<string, unknown>>;
    if (bundleRow.state === "FAILED" || bundleRow.state === "STALE") {
      // Review finding 2: never summarise another symbol's or another dataset's result as this symbol's.
      rows.push({ source: "Qualification", state: "UNAVAILABLE", detail: `Stored bundle is ${bundleRow.state}. Qualification for ${symbol} is unknown.` });
    } else if (symbolStatus === "DATA_INSUFFICIENT" || symbolStatus === "BLOCKED" || symbolStatus === "NOT_IN_UNIVERSE_AT_AS_OF") {
      rows.push({
        source: "Qualification",
        state: symbolStatus === "DATA_INSUFFICIENT" ? "MISSING" : "UNAVAILABLE",
        detail: `Stored symbol status ${symbolStatus}. This is not a finding that no setup exists.`,
      });
    } else if (candidates.length === 0) {
      rows.push({
        source: "Qualification",
        state: symbolStatus ? (bundleRow.state === "AVAILABLE" ? "AVAILABLE" : "INCOMPLETE") : "INCOMPLETE",
        detail: symbolStatus
          ? `The stored scan evaluated this symbol (${symbolStatus}) and recorded no candidate.`
          : "The stored symbol row states no status. No candidate is listed; nothing further is inferred.",
      });
    } else {
      const open = candidates.flatMap((candidate) =>
        (Array.isArray(candidate.gates) ? (candidate.gates as Array<Record<string, unknown>>) : [])
          .filter((gate) => ["MANUAL", "DATA_INSUFFICIENT", "NOT_EVALUATED"].includes(String(gate.outcome)))
          .map((gate) => `${String(gate.gate)} ${String(gate.outcome)}`),
      );
      rows.push({
        source: "Qualification",
        state: open.length || bundleRow.state !== "AVAILABLE" ? "INCOMPLETE" : "AVAILABLE",
        detail: open.length
          ? `Stored gates with evidence still open: ${open.slice(0, 6).join(", ")}${open.length > 6 ? "…" : ""}.`
          : `${candidates.length} stored candidate(s) with gate outcomes.`,
      });
    }
  }

  const explain = input.explain;
  rows.push(
    explain === null
      ? { source: "Explanation", state: "UNAVAILABLE", detail: "Not requested yet." }
      : explain.ok
        ? { source: "Explanation", state: "AVAILABLE", detail: "Stored explanation lines." }
        : { source: "Explanation", ...failure(explain, "Explanation") },
  );
  const plans = input.plans;
  if (plans !== null && !plans.ok) rows.push({ source: "Plans", ...failure(plans, "Plan records") });
  rows.push({
    source: "Data certification",
    state: fixture ? "FIXTURE" : "UNCERTIFIED",
    detail: fixture
      ? "FIXTURE_NOT_MARKET_DATA. Not an NSE result."
      : "EXPLORATORY_ONLY_NOT_CERTIFIED. Chart retrieval is not P0 certification.",
  });
  return rows;
}
