import type { CandidateStatus } from "../types/contracts";

export interface StatusPresentation {
  code: string;
  label: string;
  tone: "ok" | "fail" | "manual" | "neutral" | "blocked" | "unknown";
  dashed: boolean;
}

const CANDIDATE: Record<CandidateStatus, StatusPresentation> = {
  ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING: {
    code: "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
    label: "Actionable, manual checks pending",
    tone: "manual",
    dashed: false,
  },
  MANUAL_REVIEW: {
    code: "MANUAL_REVIEW",
    label: "Manual review",
    tone: "manual",
    dashed: true,
  },
  DATA_INSUFFICIENT: {
    code: "DATA_INSUFFICIENT",
    label: "Data insufficient",
    tone: "neutral",
    dashed: true,
  },
  REJECTED: { code: "REJECTED", label: "Rejected", tone: "fail", dashed: false },
  BLOCKED: { code: "BLOCKED", label: "Blocked", tone: "blocked", dashed: false },
};

const GATE: Record<string, StatusPresentation> = {
  PASS: { code: "PASS", label: "Pass", tone: "ok", dashed: false },
  FAIL: { code: "FAIL", label: "Fail", tone: "fail", dashed: false },
  MANUAL: { code: "MANUAL", label: "Manual", tone: "manual", dashed: false },
  DATA_INSUFFICIENT: {
    code: "DATA_INSUFFICIENT",
    label: "Data insufficient",
    tone: "neutral",
    dashed: true,
  },
  BLOCKED: { code: "BLOCKED", label: "Blocked", tone: "blocked", dashed: false },
  NOT_EVALUATED: {
    code: "NOT_EVALUATED",
    label: "Not evaluated",
    tone: "neutral",
    dashed: false,
  },
};

/** Engine restrictiveness order, for display sorting only. This does not assign a status. */
export const CANDIDATE_STATUS_ORDER: readonly CandidateStatus[] = [
  "BLOCKED",
  "REJECTED",
  "DATA_INSUFFICIENT",
  "MANUAL_REVIEW",
  "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
];

const SYMBOL_STATUS: Record<string, StatusPresentation> = {
  NO_FRESH_EXECUTION_ZONE: {
    code: "NO_FRESH_EXECUTION_ZONE",
    label: "No fresh execution zone",
    tone: "neutral",
    dashed: true,
  },
  EVALUATED: { code: "EVALUATED", label: "Evaluated", tone: "neutral", dashed: false },
  NOT_IN_UNIVERSE_AT_AS_OF: {
    code: "NOT_IN_UNIVERSE_AT_AS_OF",
    label: "Not in the universe at as-of",
    tone: "neutral",
    dashed: true,
  },
  TESTED: { code: "TESTED", label: "Tested", tone: "neutral", dashed: true },
  INVALIDATED: { code: "INVALIDATED", label: "Invalidated", tone: "blocked", dashed: false },
  UNKNOWN: { code: "UNKNOWN", label: "Unknown", tone: "unknown", dashed: true },
  FRESH: { code: "FRESH", label: "Fresh", tone: "neutral", dashed: false },
};

const LIMITATION_STATUS: Record<string, string> = {
  UNIVERSE_UNVERIFIED: "Universe unverified",
  CORPORATE_ACTIONS_UNVERIFIED: "Corporate actions unverified",
  CORPORATE_ACTION_COVERAGE_UNKNOWN: "Corporate-action coverage unknown",
  CORPORATE_ACTION_COVERAGE_INCOMPLETE: "Corporate-action coverage incomplete",
  IDENTITY_UNVERIFIED: "Identity unverified",
  IDENTITY_UNRESOLVED: "Identity unresolved",
  IDENTITY_JOINS_ARE_NOT_PERFORMED_HERE: "Identity joins are not performed here",
  ZONE_IDENTITY_UNRESOLVED: "Zone identity unresolved",
  DATA_READY_NOT_CLAIMED: "Data ready is not claimed",
  DATA_LIMITATIONS_UNAVAILABLE: "Data limitations unavailable",
  UNIVERSE_NOT_CONFIGURED: "Universe file is not configured",
  UNAVAILABLE: "Unavailable",
  NOT_SUPPLIED: "Not supplied",
};

export function presentStatus(code: string): StatusPresentation {
  if (code in CANDIDATE) return CANDIDATE[code as CandidateStatus];
  if (code in GATE) return GATE[code];
  if (code in SYMBOL_STATUS) return SYMBOL_STATUS[code];
  if (code in LIMITATION_STATUS) {
    return { code, label: LIMITATION_STATUS[code] ?? code, tone: "neutral", dashed: true };
  }
  return {
    code,
    label: `Unknown status: ${code}`,
    tone: "unknown",
    dashed: true,
  };
}

export function presentLimitation(code: string): string {
  return LIMITATION_STATUS[code] ?? `Unknown limitation: ${code}`;
}

export function statusRank(code: string): number {
  const index = CANDIDATE_STATUS_ORDER.indexOf(code as CandidateStatus);
  return index === -1 ? CANDIDATE_STATUS_ORDER.length + 1 : index;
}

export function unavailableText(): string {
  return "Unavailable";
}
