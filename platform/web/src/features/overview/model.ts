import type { OverviewCounts } from "../../types/contracts";

export const CANDIDATE_STATUSES = [
  "BLOCKED",
  "REJECTED",
  "DATA_INSUFFICIENT",
  "MANUAL_REVIEW",
  "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
] as const;

/** A missing scan is null. A missing status inside a present map stays null, not zero. An explicit 0 stays 0. */
export function statusCount(
  counts: OverviewCounts | null | undefined,
  status: string,
): number | null {
  if (counts == null) return null;
  const map = counts.candidate_status ?? {};
  if (!Object.prototype.hasOwnProperty.call(map, status)) return null;
  const value = map[status];
  return typeof value === "number" ? value : null;
}

export function numericField(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
