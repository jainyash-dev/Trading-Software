/**
 * Product information architecture (P10-1).
 * Route ids are stable so earlier deep links keep working. `status` states how much of the
 * screen is backed by a real API: LIVE (connected), PARTIAL (some capability has no backend),
 * NOT_IMPLEMENTED (no backend; the screen explains the capability honestly).
 */
export type RouteGroup = "Overview" | "Research" | "Trading" | "Intelligence" | "System";
export type RouteStatus = "LIVE" | "PARTIAL" | "NOT_IMPLEMENTED";

export const ROUTE_GROUPS: readonly RouteGroup[] = ["Overview", "Research", "Trading", "Intelligence", "System"];

export const ROUTES = [
  { id: "overview", label: "Market Overview", group: "Overview", available: true, status: "LIVE" },
  { id: "watchlists", label: "Watchlists", group: "Overview", available: true, status: "LIVE" },
  { id: "analysis", label: "Stock Analysis", group: "Research", available: true, status: "LIVE" },
  { id: "scanner", label: "Opportunity Scanner", group: "Research", available: true, status: "LIVE" },
  { id: "opportunities", label: "Opportunities", group: "Research", available: true, status: "LIVE" },
  { id: "history", label: "Scan History", group: "Research", available: true, status: "LIVE" },
  { id: "plans", label: "Trade Plans", group: "Trading", available: true, status: "LIVE" },
  { id: "portfolio", label: "Portfolio", group: "Trading", available: true, status: "LIVE" },
  { id: "risk", label: "Risk Overview", group: "Trading", available: true, status: "LIVE" },
  { id: "journal", label: "Trading Journal", group: "Trading", available: true, status: "LIVE" },
  { id: "backtest", label: "Backtesting", group: "Intelligence", available: true, status: "PARTIAL" },
  { id: "analytics", label: "Strategy Analytics", group: "Intelligence", available: false, status: "NOT_IMPLEMENTED" },
  { id: "reports", label: "Research Reports", group: "Intelligence", available: true, status: "LIVE" },
  { id: "assistant", label: "AI Research Assistant", group: "Intelligence", available: true, status: "PARTIAL" },
  { id: "paper", label: "Shadow / Paper", group: "Intelligence", available: false, status: "NOT_IMPLEMENTED" },
  { id: "data", label: "Data Health", group: "System", available: true, status: "LIVE" },
  { id: "jobs", label: "Jobs and Monitoring", group: "System", available: true, status: "PARTIAL" },
  { id: "settings", label: "Settings", group: "System", available: true, status: "LIVE" },
] as const satisfies ReadonlyArray<{ id: string; label: string; group: RouteGroup; available: boolean; status: RouteStatus }>;

export type RouteId = (typeof ROUTES)[number]["id"];
export type RouteDef = (typeof ROUTES)[number];

export function isRoute(value: string): value is RouteId {
  return ROUTES.some((route) => route.id === value);
}

export function routeDef(id: RouteId): RouteDef {
  return ROUTES.find((route) => route.id === id) ?? ROUTES[0];
}

export function parseHash(hash: string): { route: RouteId; query: string } {
  const raw = hash.replace(/^#/, "");
  const trimmed = raw.startsWith("/") ? raw.slice(1) : raw;
  const [path, search = ""] = trimmed.split("?");
  let id = path;
  try {
    id = decodeURIComponent(path);
  } catch {
    id = path;
  }
  id = id.replace(/\/$/, "");
  return { route: isRoute(id) ? id : "overview", query: search };
}

export function routeFromHash(hash: string): RouteId {
  return parseHash(hash).route;
}
