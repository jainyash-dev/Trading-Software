/** Hash-query fields the screens are allowed to restore. Anything else is ignored. */

const TOKEN = /^[A-Za-z0-9._:-]{1,120}$/;
const AS_OF = /^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9:.+Z-]{1,32})?$/;
const KNOWN = new Set([
  "scan",
  "symbol",
  "zone",
  "entry",
  "as_of",
  "dataset_id",
  "fixtures",
  "timeframe",
  "watchlist",
  "panel",
  "workflow",
  "q",
  "sort",
  "plan",
  "plan_state",
]);

export interface ViewQuery {
  scan: string;
  symbol: string;
  zone: string;
  entry: string;
  asOf: string;
  datasetId: string;
  timeframe: "" | "M" | "W" | "D";
  fixtures: boolean;
  plan: string;
  planState: string;
  ignored: string[];
  rejected: string[];
}

export function readViewQuery(query: string): ViewQuery {
  let params: URLSearchParams;
  try {
    params = new URLSearchParams(query);
  } catch {
    return {
      scan: "",
      symbol: "",
      zone: "",
      entry: "",
      asOf: "",
      datasetId: "",
      timeframe: "",
      fixtures: false,
      plan: "",
      planState: "",
      ignored: [],
      rejected: ["query"],
    };
  }
  const ignored: string[] = [];
  const rejected: string[] = [];
  for (const key of params.keys()) {
    if (!KNOWN.has(key)) ignored.push(key);
  }
  return {
    scan: take(params, "scan", rejected),
    symbol: take(params, "symbol", rejected).toUpperCase(),
    zone: take(params, "zone", rejected),
    entry: take(params, "entry", rejected),
    asOf: takeAsOf(params, rejected),
    datasetId: take(params, "dataset_id", rejected),
    timeframe: takeTimeframe(params, rejected),
    fixtures: params.get("fixtures") === "1",
    plan: take(params, "plan", rejected),
    planState: take(params, "plan_state", rejected),
    ignored,
    rejected,
  };
}

function takeTimeframe(params: URLSearchParams, rejected: string[]): "" | "M" | "W" | "D" {
  const raw = params.get("timeframe");
  if (!raw) return "";
  if (raw === "M" || raw === "W" || raw === "D") return raw;
  rejected.push("timeframe");
  return "";
}

/** Build a hash-query string preserving known fields and updating overrides. */
export function writeViewQuery(current: string, patch: Partial<Record<string, string | null>>): string {
  const params = new URLSearchParams(current.startsWith("?") ? current.slice(1) : current);
  for (const [key, value] of Object.entries(patch)) {
    if (!KNOWN.has(key)) continue;
    if (value === null || value === undefined || value === "") params.delete(key);
    else params.set(key, value);
  }
  return params.toString();
}

function take(params: URLSearchParams, key: string, rejected: string[]): string {
  const raw = params.get(key);
  if (!raw) return "";
  if (!TOKEN.test(raw)) {
    rejected.push(key);
    return "";
  }
  return raw;
}

function takeAsOf(params: URLSearchParams, rejected: string[]): string {
  const raw = params.get("as_of");
  if (!raw) return "";
  if (!AS_OF.test(raw)) {
    rejected.push("as_of");
    return "";
  }
  return raw;
}
