import { FIXTURE_LABEL, PLATFORM_SCHEMA } from "../types/contracts";

export interface Call {
  path: string;
  search: string;
  method: string;
  headers: Headers;
  body: unknown;
}

export function envelope(data: unknown, status = 200, fixture = false): Response {
  return json(
    {
      platform_schema: PLATFORM_SCHEMA,
      data,
      meta: fixture ? { fixture: true, fixture_label: FIXTURE_LABEL } : { fixture: false },
    },
    status,
  );
}

export function failure(status: number, code: string, message: string): Response {
  return json({ error: { code, message, details: {} } }, status);
}

export function json(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export interface PlatformOptions {
  health?: Record<string, unknown>;
  scans?: Array<Record<string, unknown> & { fixture?: boolean }>;
  watchlists?: Array<Record<string, unknown>>;
  instruments?: Array<Record<string, unknown>>;
  datasets?: Array<Record<string, unknown>>;
  universe?: Record<string, unknown>;
  overview?: Record<string, unknown>;
  calendar?: Record<string, unknown>;
  portfolio?: Record<string, unknown> | null;
  journal?: Record<string, unknown> | null;
  journalDetail?: Record<string, unknown> | null;
  journalPerformance?: Record<string, unknown> | null;
  handle?: (call: Call) => Response | Promise<Response> | null;
}

const defaultHealth = {
  outcome: "WARNING",
  scheduler_state: "STOPPED",
  database_files: {
    platform: { configured: true, reachable: true },
    research: { configured: false, reachable: false },
  },
  last_successful_ingest_date: "2024-06-14",
  last_scan_run_id: null,
  last_scan: null,
  last_scan_state: "UNAVAILABLE",
  data_limitations: ["DATA_READY_NOT_CLAIMED", "UNIVERSE_UNVERIFIED"],
  data_ready: false,
  orders_placed: false,
};

export function createPlatform(options: PlatformOptions = {}) {
  const calls: Call[] = [];
  const fetcher = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://127.0.0.1");
    const headers = new Headers(init?.headers);
    let body: unknown = null;
    if (typeof init?.body === "string" && init.body) {
      try {
        body = JSON.parse(init.body) as unknown;
      } catch {
        body = init.body;
      }
    }
    const call: Call = {
      path: url.pathname,
      search: url.search,
      method: (init?.method ?? "GET").toUpperCase(),
      headers,
      body,
    };
    calls.push(call);
    const custom = await options.handle?.(call);
    if (custom) return custom;
    return route(url, call, options);
  }) as typeof fetch;
  return { fetcher, calls };
}

function route(url: URL, call: Call, options: PlatformOptions): Response {
  if (call.path === "/api/v1/session" || call.path === "/api/v1/session/bootstrap") {
    return envelope({ authenticated: true, auth: "cookie" });
  }
  if (call.path === "/api/v1/health") return envelope(options.health ?? defaultHealth);
  if (call.path === "/api/v1/overview") {
    return envelope(
      options.overview ?? {
        state: "UNAVAILABLE",
        as_of: null,
        dataset_id: null,
        counts: null,
        calendar: null,
        index: null,
        sector: null,
        breadth: null,
        index_state: "UNAVAILABLE",
        sector_state: "UNAVAILABLE",
        breadth_state: "UNAVAILABLE",
      },
    );
  }
  if (call.path === "/api/v1/datasets") {
    const datasets = options.datasets ?? [
      {
        dataset_id: "local-dataset",
        manifest_sha256: "abc123",
        file_count: 2,
        research_validation: false,
        data_ready: false,
        fixture: false,
      },
    ];
    return envelope({ datasets, limitations: ["DATA_READY_NOT_CLAIMED"] }, 200, datasets.some((row) => row.fixture === true));
  }
  if (call.path === "/api/v1/universe") {
    return envelope(
      options.universe ?? {
        as_of: "2024-06-14",
        name: "SUPPORTED",
        members: [{ symbol: "TCS", series: "EQ", isin: null, verified: false }],
        limitations: ["UNIVERSE_UNVERIFIED"],
        certified: false,
        full_universe_scan: false,
      },
    );
  }
  if (call.path === "/api/v1/calendar") {
    return envelope(options.calendar ?? { date: "2024-06-14", status: "CONFIRMED", classification: "NORMAL", reason: null });
  }
  if (call.path === "/api/v1/scans" && call.method === "GET") {
    const include = url.searchParams.get("include_fixtures") === "true";
    const all = options.scans ?? [];
    const scans = include ? all : all.filter((row) => row.fixture !== true);
    return envelope({ scans, next_cursor: null }, 200, scans.some((row) => row.fixture === true));
  }
  if (call.path === "/api/v1/watchlists" && call.method === "GET") {
    return envelope({ watchlists: options.watchlists ?? [] });
  }
  if (call.path === "/api/v1/scan-configs" && call.method === "GET") return envelope({ scan_configs: [] });
  if (call.path === "/api/v1/instruments") {
    const needle = (url.searchParams.get("query") ?? "").toUpperCase();
    const instruments = (options.instruments ?? []).filter((row) => {
      const haystack = `${row.symbol ?? ""} ${row.name ?? ""} ${row.isin ?? ""}`.toUpperCase();
      return needle.length > 0 && haystack.includes(needle);
    });
    return envelope({ instruments });
  }
  if (call.path === "/api/v1/portfolio" && call.method === "GET") {
    if (options.portfolio === null) {
      return failure(409, "CONFLICT", "ONE_ORDER_PER_ZONE: journal entry already holds this zone");
    }
    return envelope(
      options.portfolio ?? {
        trades_triggered_this_month: 0,
        monthly_cap: 10,
        open_positions: 0,
        open_position_cap: 10,
        valuation: null,
        valuation_state: "UNAVAILABLE",
        unrealised_pnl: "UNAVAILABLE",
        exposure: null,
        exposure_state: "UNAVAILABLE",
        portfolio_risk: null,
        portfolio_risk_state: "UNAVAILABLE",
        sector: null,
        sector_state: "UNAVAILABLE",
        drawdown: null,
        drawdown_state: "UNAVAILABLE",
        research_use: "FIXTURE_NOT_MARKET_DATA",
        zones: [],
        authorises_order: false,
        note: "Counts come from the research journal only.",
      },
    );
  }
  if (call.path === "/api/v1/journal" && call.method === "GET") {
    if (options.journal === null) {
      return failure(500, "INTERNAL", "The journal could not be read");
    }
    return envelope(
      options.journal ?? {
        entries: [],
        total: 0,
        limit: 100,
        offset: 0,
        authorises_order: false,
        evidence_class: "JOURNAL_DESCRIPTIVE",
      },
    );
  }
  if (call.path === "/api/v1/journal/performance" && call.method === "GET") {
    return envelope(
      options.journalPerformance ?? {
        evidence_class: "JOURNAL_DESCRIPTIVE",
        limitations: ["Not certified strategy performance."],
        totals: {
          recorded_trades: 0,
          open_trades: 0,
          closed_trades: 0,
          wins: 0,
          losses: 0,
          gross_realised_pnl: null,
          net_realised_pnl: null,
          net_state: "UNAVAILABLE",
          known_charges_paise: null,
          reviewed: 0,
          unreviewed: 0,
        },
        authorises_order: false,
      },
    );
  }
  if (call.path.startsWith("/api/v1/journal/") && call.method === "GET" && !call.path.includes("/attachments/")) {
    return envelope(
      options.journalDetail ?? {
        state: "PLANNED",
        charges_state: "ABSENT",
        entry: { entry_id: 1, symbol: "SYN" },
        events: [],
        executions: [],
        notes: [],
        attachments: [],
        review: { review_status: "NOT_REVIEWED", outcome_class: "NOT_REVIEWED", mistake_category: "NOT_REVIEWED" },
        planned_versus_actual: { state: "PLANNED_ONLY", planned: {}, actual: {}, deltas: {} },
        authorises_order: false,
      },
    );
  }
  return failure(404, "NOT_FOUND", `No test route for ${call.method} ${call.path}`);
}
