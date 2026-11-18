import type { JobProgress, ResearchSymbol } from "../../types/contracts";

export const SCAN_MODES = ["MANUAL", "SCHEDULED", "REPLAY"] as const;
export const TRADE_TYPES = ["MIT", "WIT-75", "WIT-125"] as const;
export const TERMINAL_JOB_STATES = [
  "SUCCEEDED_COMPLETE",
  "SUCCEEDED_PARTIAL",
  "FAILED",
  "INTERRUPTED",
  "CANCELLED",
  "SKIPPED_HOLIDAY",
  "SKIPPED_UNRESOLVED_CALENDAR",
] as const;

const SYMBOL_RE = /^[A-Z0-9][A-Z0-9&.-]{0,24}$/;

/**
 * Canonical stored status. nse/research reports emit `status` on symbol and candidate rows
 * (as platform ingest and planning read it). `symbol_status` / `candidate_status` are legacy
 * client names kept only as a fallback.
 */
export function symbolStatusOf(symbol: { status?: string; symbol_status?: string } | null | undefined): string | undefined {
  return symbol?.status || symbol?.symbol_status || undefined;
}

export function candidateStatusOf(candidate: { status?: string; candidate_status?: string } | null | undefined): string | undefined {
  return candidate?.status || candidate?.candidate_status || undefined;
}

export interface RiskDraft {
  kind: "pct" | "amount";
  capital: string;
  rpt: string;
  stage: string;
}

export interface ScanDraft {
  mode: string;
  tradeType: string;
  universeMode: "SUPPORTED" | "LIST";
  symbols: string[];
  asOf: string;
  datasetId: string;
  risk: RiskDraft | null;
}

export function isTerminalJob(state: string | null | undefined): boolean {
  return !!state && (TERMINAL_JOB_STATES as readonly string[]).includes(state);
}

export function isActiveJob(state: string | null | undefined): boolean {
  return state === "PENDING_DATA" || state === "VALIDATING" || state === "RUNNING";
}

/** Counts and units from the job. Never a percentage. */
export function progressLabel(progress: JobProgress | null | undefined): string | null {
  if (!progress) return null;
  const unit = typeof progress.unit === "string" && progress.unit ? progress.unit : "symbols";
  const done = typeof progress.done === "number" ? progress.done : null;
  const total = typeof progress.total === "number" ? progress.total : null;
  if (done !== null && total !== null) return `${done} of ${total} ${unit}`;
  if (done !== null) return `${done} ${unit}`;
  if (total !== null) return `Total ${total} ${unit}`;
  return null;
}

export function forbiddenParameterPaths(parameters: unknown): string[] {
  const hits: string[] = [];
  walk(parameters, "", hits);
  return hits;
}

function walk(value: unknown, path: string, hits: string[]) {
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    const next = path ? `${path}.${key}` : key;
    if (key.toLowerCase().replace(/_/g, "") === "maxbasecandles") hits.push(next);
    walk(child, next, hits);
  }
}

export function applyConfigParameters(draft: ScanDraft, parameters: Record<string, unknown>): { draft: ScanDraft; ignored: string[] } {
  const ignored = new Set(forbiddenParameterPaths(parameters));
  const next: ScanDraft = { ...draft, symbols: [...draft.symbols], risk: draft.risk ? { ...draft.risk } : null };
  if (typeof parameters.mode === "string" && (SCAN_MODES as readonly string[]).includes(parameters.mode)) next.mode = parameters.mode;
  if (typeof parameters.trade_type === "string" && (TRADE_TYPES as readonly string[]).includes(parameters.trade_type)) {
    next.tradeType = parameters.trade_type;
  }
  if (parameters.universe === "SUPPORTED") {
    next.universeMode = "SUPPORTED";
    next.symbols = [];
  } else if (Array.isArray(parameters.universe)) {
    next.universeMode = "LIST";
    next.symbols = parameters.universe.filter((item): item is string => typeof item === "string").map((item) => item.trim().toUpperCase());
  }
  if (typeof parameters.as_of === "string") next.asOf = parameters.as_of;
  if (parameters.risk && typeof parameters.risk === "object") {
    const risk = parameters.risk as Record<string, unknown>;
    next.risk = {
      kind: typeof risk.rpt_amount === "string" || typeof risk.rpt_amount === "number" ? "amount" : "pct",
      capital: String(risk.capital ?? ""),
      rpt: String(risk.rpt_pct ?? risk.rpt_amount ?? ""),
      stage: String(risk.stage ?? ""),
    };
  }
  const appliedKeys = new Set(["mode", "trade_type", "universe", "as_of", "risk"]);
  for (const key of Object.keys(parameters)) {
    if (!appliedKeys.has(key)) ignored.add(key);
  }
  return { draft: next, ignored: [...ignored] };
}

export function scanRequestBody(draft: ScanDraft): { ok: true; body: Record<string, unknown> } | { ok: false; message: string } {
  if (!(SCAN_MODES as readonly string[]).includes(draft.mode)) {
    return { ok: false, message: "mode must be MANUAL, SCHEDULED, or REPLAY" };
  }
  if (!(TRADE_TYPES as readonly string[]).includes(draft.tradeType)) {
    return { ok: false, message: "trade_type is not a known research trade type" };
  }
  if (!draft.asOf.trim()) return { ok: false, message: "as_of is required" };
  if (!draft.datasetId.trim()) return { ok: false, message: "dataset_id is required" };
  let universe: string | string[];
  if (draft.universeMode === "SUPPORTED") universe = "SUPPORTED";
  else {
    if (draft.symbols.length === 0) return { ok: false, message: "universe must be SUPPORTED or a symbol list" };
    if (draft.symbols.length > 150) return { ok: false, message: "A symbol list is limited to 150 tickers" };
    for (const symbol of draft.symbols) {
      if (!SYMBOL_RE.test(symbol)) return { ok: false, message: "A universe symbol is not a usable ticker" };
    }
    universe = [...draft.symbols];
  }
  const body: Record<string, unknown> = {
    mode: draft.mode,
    as_of: draft.asOf.trim(),
    trade_type: draft.tradeType,
    universe,
    dataset_id: draft.datasetId,
  };
  if (draft.risk) {
    const capital = draft.risk.capital.trim();
    const rpt = draft.risk.rpt.trim();
    if (!capital) return { ok: false, message: "risk.capital is required when risk is set" };
    if (!rpt) return { ok: false, message: "risk needs exactly one of rpt_amount or rpt_pct" };
    body.risk = {
      capital,
      rpt_amount: draft.risk.kind === "amount" ? rpt : null,
      rpt_pct: draft.risk.kind === "pct" ? rpt : null,
      stage: draft.risk.stage ? draft.risk.stage : null,
    };
  }
  return { ok: true, body };
}

export function configParameters(draft: ScanDraft): Record<string, unknown> {
  return {
    mode: draft.mode,
    trade_type: draft.tradeType,
    universe: draft.universeMode === "SUPPORTED" ? "SUPPORTED" : [...draft.symbols],
  };
}

export function listedStatuses(symbol: ResearchSymbol): string[] {
  const found: string[] = [];
  const push = (value: unknown) => {
    if (typeof value === "string" && value && !found.includes(value)) found.push(value);
  };
  push(symbolStatusOf(symbol));
  for (const candidate of symbol.candidates ?? []) {
    push(candidateStatusOf(candidate));
    for (const gate of candidate.gates ?? []) push(gate.outcome);
    for (const group of candidate.deciding_gates ?? []) {
      push(group.status);
      for (const gate of group.gates ?? []) push(gate.outcome);
    }
  }
  return found;
}

export function listedTimeframes(symbol: ResearchSymbol): string[] {
  const found: string[] = [];
  for (const candidate of symbol.candidates ?? []) {
    const zone = candidate.zone;
    const tf = zone && (typeof zone.tf === "string" ? zone.tf : typeof zone.timeframe === "string" ? zone.timeframe : null);
    if (tf && !found.includes(tf)) found.push(tf);
  }
  return found;
}

export function qualityCodes(symbol: ResearchSymbol): string[] {
  const found: string[] = [];
  for (const item of symbol.limitations ?? []) if (!found.includes(item)) found.push(item);
  for (const finding of symbol.findings ?? []) {
    if (finding && typeof finding === "object" && "code" in finding && typeof (finding as { code?: unknown }).code === "string") {
      const code = (finding as { code: string }).code;
      if (!found.includes(code)) found.push(code);
    }
  }
  return found;
}

export interface ResultFilter {
  symbol: string;
  status: string;
  timeframe: string;
  quality: string;
}

/** Presentation filter. Input order is preserved and statuses are not rewritten. */
export function filterSymbols(symbols: ResearchSymbol[], filter: ResultFilter): ResearchSymbol[] {
  const query = filter.symbol.trim().toUpperCase();
  return symbols.filter((symbol) => {
    const name = (symbol.symbol ?? "").toUpperCase();
    if (query && !name.includes(query)) return false;
    if (filter.status && !listedStatuses(symbol).includes(filter.status)) return false;
    if (filter.timeframe && !listedTimeframes(symbol).includes(filter.timeframe)) return false;
    if (filter.quality && !qualityCodes(symbol).includes(filter.quality) && symbolStatusOf(symbol) !== filter.quality) return false;
    return true;
  });
}

export function textList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

export function fieldText(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  return null;
}

// --- P3-D / FR-3.4 / OI-002: why nothing qualified ------------------------------------------

/** Canonical stored values (nse/research/models.py, nse/research/scanner.py). */
export const ACTIONABLE_STATUS = "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING";

export type ScanOutcomeKind = "UNAVAILABLE" | "FAILED" | "QUALIFIED" | "NOTHING_QUALIFIED" | "EMPTY";

export interface ScanOutcome {
  kind: ScanOutcomeKind;
  headline: string;
  /** One line per stored reason class. Each line cites stored statuses or gates; nothing is inferred. */
  lines: Array<{ code: string; text: string }>;
}

interface OutcomeEnvelope {
  completeness?: string;
  dataset_id?: string | null;
  symbols_not_opened?: string[];
  counts?: { candidate_status?: Record<string, number> };
  symbols?: Array<{
    symbol?: string;
    status?: string;
    symbol_status?: string;
    reasons?: string[];
    blocked_zones?: unknown[];
    candidates?: Array<{ status?: string; candidate_status?: string; deciding_gates?: Array<{ status?: string; gates?: Array<{ gate?: string; outcome?: string }> }> }>;
  }>;
}

function tally(values: string[]): string {
  const counts = new Map<string, number>();
  for (const value of values) counts.set(value, (counts.get(value) || 0) + 1);
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([value, count]) => `${value} ×${count}`)
    .join(", ");
}

export function scanOutcome(input: {
  envelope: OutcomeEnvelope | null;
  connected: boolean;
  error: { code?: string; message?: string } | null;
  /** Current local dataset ids from /datasets, or null when not loaded (staleness unknown). */
  currentDatasetIds: string[] | null;
}): ScanOutcome | null {
  const { envelope } = input;
  if (!envelope) {
    if (!input.connected || input.error?.code === "DISCONNECTED") {
      return { kind: "UNAVAILABLE", headline: "Scanner unavailable. No scan result was read; this is not a scan with zero candidates.", lines: [] };
    }
    if (input.error && input.error.code !== "NOT_FOUND") {
      return { kind: "UNAVAILABLE", headline: `The stored scan could not be read (${input.error.code}). This is not a scan with zero candidates.`, lines: [] };
    }
    return null;
  }
  const lines: ScanOutcome["lines"] = [];
  if (envelope.completeness === "FAILED") {
    return { kind: "FAILED", headline: "Stored completeness is FAILED. A failed scan is not a successful scan with zero candidates.", lines };
  }
  const symbols = envelope.symbols ?? [];
  const candidates = symbols.flatMap((row) => (row.candidates ?? []).map((candidate) => ({ symbol: row.symbol ?? "?", candidate })));
  const statusOf = (value: string | undefined) => value || "UNAVAILABLE";
  const qualified = candidates.filter((row) => candidateStatusOf(row.candidate) === ACTIONABLE_STATUS);
  const notOpened = envelope.symbols_not_opened ?? [];
  if (envelope.completeness && envelope.completeness !== "COMPLETE") {
    lines.push({
      code: "PARTIAL_SCAN",
      text: `Scan is ${envelope.completeness}. ${notOpened.length} symbol(s) not opened${notOpened.length ? ` (${notOpened.slice(0, 8).join(", ")}${notOpened.length > 8 ? "…" : ""})` : ""}. Their outcome is unknown, not zero.`,
    });
  } else if (notOpened.length) {
    lines.push({ code: "PARTIAL_SCAN", text: `${notOpened.length} symbol(s) were not opened. Their outcome is unknown, not zero.` });
  }
  if (!envelope.completeness) {
    lines.push({ code: "COMPLETENESS_UNSTATED", text: "The stored scan does not state its completeness. Treat it as incomplete." });
  }
  if (input.currentDatasetIds && envelope.dataset_id && !input.currentDatasetIds.includes(envelope.dataset_id)) {
    lines.push({
      code: "STALE_DATASET",
      text: `Scan dataset ${envelope.dataset_id} is not the current local dataset. This scan does not describe the current files.`,
    });
  }
  const bySymbolStatus = (status: string) => symbols.filter((row) => symbolStatusOf(row) === status);
  const insufficient = bySymbolStatus("DATA_INSUFFICIENT");
  if (insufficient.length) {
    const reasons = insufficient.flatMap((row) => row.reasons ?? []);
    lines.push({
      code: "EVIDENCE_MISSING",
      text: `${insufficient.length} symbol(s) DATA_INSUFFICIENT${reasons.length ? `: ${tally(reasons).slice(0, 240)}` : ""}. Missing data is not a rejection.`,
    });
  }
  const notInUniverse = bySymbolStatus("NOT_IN_UNIVERSE_AT_AS_OF");
  if (notInUniverse.length) lines.push({ code: "NOT_IN_UNIVERSE", text: `${notInUniverse.length} symbol(s) NOT_IN_UNIVERSE_AT_AS_OF.` });
  const blockedSymbols = bySymbolStatus("BLOCKED");
  if (blockedSymbols.length) {
    lines.push({ code: "SYMBOL_BLOCKED", text: `${blockedSymbols.length} symbol(s) BLOCKED${tally(blockedSymbols.flatMap((row) => row.reasons ?? [])) ? `: ${tally(blockedSymbols.flatMap((row) => row.reasons ?? [])).slice(0, 240)}` : ""}.` });
  }
  const noZone = bySymbolStatus("NO_FRESH_EXECUTION_ZONE");
  if (noZone.length) {
    lines.push({ code: "NO_FRESH_ZONE", text: `${noZone.length} symbol(s) NO_FRESH_EXECUTION_ZONE: the engine found no fresh, unbreached demand zone to evaluate.` });
  }
  const blockedZones = symbols.reduce((sum, row) => sum + (row.blocked_zones?.length ?? 0), 0);
  if (blockedZones) lines.push({ code: "ZONES_BLOCKED", text: `${blockedZones} zone(s) were recorded in blocked_zones (tested, invalidated, or unknown freshness).` });
  for (const status of ["REJECTED", "MANUAL_REVIEW", "DATA_INSUFFICIENT", "BLOCKED"]) {
    const rows = candidates.filter((row) => candidateStatusOf(row.candidate) === status);
    if (!rows.length) continue;
    const gates = rows.flatMap((row) =>
      (row.candidate.deciding_gates ?? []).flatMap((group) => (group.gates ?? []).map((gate) => `${gate.gate ?? "gate"} ${gate.outcome ?? ""}`.trim())),
    );
    const listed = rows.some((row) => row.candidate.deciding_gates !== undefined);
    const code = status === "REJECTED" ? "CANDIDATES_REJECTED" : status === "MANUAL_REVIEW" ? "EVIDENCE_INCOMPLETE" : status === "DATA_INSUFFICIENT" ? "EVIDENCE_MISSING" : "CANDIDATES_BLOCKED";
    lines.push({
      code,
      text: `${rows.length} candidate(s) ${status}. Deciding gates: ${gates.length ? tally(gates) : listed ? "none listed" : "not stored in this envelope"}.`,
    });
  }
  const other = candidates.filter(
    (row) => ![ACTIONABLE_STATUS, "REJECTED", "MANUAL_REVIEW", "DATA_INSUFFICIENT", "BLOCKED"].includes(statusOf(candidateStatusOf(row.candidate))),
  );
  if (other.length) lines.push({ code: "STATUS_UNAVAILABLE", text: `${other.length} candidate(s) have no recognised stored status. Not counted as qualified.` });
  const stored = envelope.counts?.candidate_status;
  if (stored && typeof stored[ACTIONABLE_STATUS] === "number" && stored[ACTIONABLE_STATUS] !== qualified.length) {
    lines.push({
      code: "COUNTS_DISAGREE",
      text: `Stored counts say ${stored[ACTIONABLE_STATUS]} ${ACTIONABLE_STATUS}; the stored symbol rows hold ${qualified.length}. The rows are shown; resolve before relying on either.`,
    });
  }
  if (symbols.length === 0) {
    return {
      kind: "EMPTY",
      headline: notOpened.length || envelope.completeness !== "COMPLETE" ? "No symbol rows were stored. The scan did not open its symbols; this is not a zero-candidate result." : "The stored scan holds no symbol rows.",
      lines,
    };
  }
  if (qualified.length) {
    return {
      kind: "QUALIFIED",
      headline: `${qualified.length} candidate(s) are ${ACTIONABLE_STATUS}. Manual checks are still pending. Not an order.`,
      lines,
    };
  }
  return {
    kind: "NOTHING_QUALIFIED",
    headline: `No candidate reached ${ACTIONABLE_STATUS} in this stored scan.${lines.some((line) => line.code === "PARTIAL_SCAN") ? " The scan is partial, so this covers only the symbols it opened." : ""}`,
    lines: lines.length ? lines : [{ code: "NO_REASON_STORED", text: "The stored rows record no candidate and no reason class. Nothing further is inferred." }],
  };
}
