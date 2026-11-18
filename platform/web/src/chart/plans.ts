/**
 * FR-4.9: trade-plan entry, stop, and target lines as a third chart overlay, labelled as a plan.
 *
 * Presentation only. Levels come from the stored plan record (`selected`, the printed buffer the
 * owner chose at approval). Nothing is calculated, picked, or defaulted here. A plan without a
 * selected buffer has no lines. A cancelled, rejected, expired, or closed plan is never drawn as
 * active. A plan whose journal state cannot be confirmed (P4-IR-04) is withheld, not guessed.
 */

export type PlanLineKind = "entry" | "stop" | "target";

export interface PlanLine {
  planId: string;
  kind: PlanLineKind;
  price: number;
  label: string;
}

export interface PlanNote {
  planId: string;
  state: string;
  reason: string;
}

export interface PlanOverlay {
  lines: PlanLine[];
  notes: PlanNote[];
}

const INACTIVE = new Set(["CANCELLED", "REJECTED", "EXPIRED"]);
const LIVE_JOURNAL = new Set(["PLANNED", "OPEN"]);

function level(selected: Record<string, unknown>, key: string): number | null {
  const raw = selected[key];
  if (raw === null || raw === undefined || raw === "" || typeof raw === "boolean") return null;
  const value = Number(raw);
  return Number.isFinite(value) && value > 0 ? value : null;
}

export function planOverlayFromRecords(
  records: ReadonlyArray<Record<string, unknown>>,
  scope: { symbol: string; scanKey: string },
): PlanOverlay {
  const lines: PlanLine[] = [];
  const notes: PlanNote[] = [];
  for (const record of records) {
    const planId = String(record.plan_id || "");
    const state = String(record.state || "UNKNOWN");
    if (!planId) continue;
    if (String(record.symbol || "").toUpperCase() !== scope.symbol.toUpperCase()) {
      notes.push({ planId, state, reason: "Different symbol. Not drawn on this chart." });
      continue;
    }
    if (String(record.scan_key || "") !== scope.scanKey) {
      notes.push({ planId, state, reason: `Plan belongs to scan ${String(record.scan_key || "unknown")}, not this scan. Not drawn.` });
      continue;
    }
    if (INACTIVE.has(state)) {
      notes.push({ planId, state, reason: `${state}. Inactive plans are not drawn.` });
      continue;
    }
    if (state !== "APPROVED") {
      notes.push({ planId, state, reason: `${state}. No buffer is selected yet, so there are no plan lines.` });
      continue;
    }
    const sync = String(record.journal_sync || "");
    const journal = record.journal_state == null ? null : String(record.journal_state);
    if (sync !== "IN_SYNC" || journal === null) {
      notes.push({ planId, state, reason: `Journal state is not confirmed (${sync || "unknown"}). Plan lines are withheld.` });
      continue;
    }
    if (record.journal_zone_invalidated === true) {
      notes.push({ planId, state, reason: "The journal recorded ZONE_INVALIDATED for this entry. Plan lines are withheld." });
      continue;
    }
    if (!LIVE_JOURNAL.has(journal)) {
      notes.push({ planId, state, reason: `Journal entry is ${journal}. Not drawn as an active plan.` });
      continue;
    }
    const selected = (record.selected || null) as Record<string, unknown> | null;
    if (!selected) {
      notes.push({ planId, state, reason: "Approved plan has no recorded levels. Nothing is drawn." });
      continue;
    }
    const short = planId.replace(/^plan-/, "").slice(0, 6);
    const drawn: PlanLine[] = [];
    const missing: string[] = [];
    for (const [kind, key] of [
      ["entry", "entry"],
      ["stop", "stop"],
      ["target", "target"],
    ] as const) {
      const price = level(selected, key);
      if (price === null) missing.push(kind);
      else drawn.push({ planId, kind, price, label: `PLAN ${short} ${kind} (journal ${journal})` });
    }
    if (missing.length) {
      notes.push({ planId, state, reason: `Recorded level missing or invalid: ${missing.join(", ")}. Those lines are not drawn.` });
    }
    lines.push(...drawn);
  }
  return { lines, notes };
}

export function planLineColor(kind: PlanLineKind): string {
  if (kind === "entry") return "#3b6fb6";
  if (kind === "stop") return "#b04a4a";
  return "#3f8f5a";
}
