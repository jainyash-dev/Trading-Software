import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";
import { ROUTE_GROUPS, ROUTES } from "../navigation/routes";
import { createPlatform, envelope } from "../test/platformFetch";
import { formatDate, formatInr, formatPaise, formatPrice, formatQuantity, toNumber } from "../design/format";

const offline = (async () => {
  throw new TypeError("offline");
}) as typeof fetch;

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.dataset.theme = "dark";
  window.location.hash = "";
});

describe("P10 information architecture", () => {
  it("groups every route under the five product groups with a capability status", () => {
    expect(ROUTE_GROUPS).toEqual(["Overview", "Research", "Trading", "Intelligence", "System"]);
    for (const route of ROUTES) {
      expect(ROUTE_GROUPS).toContain(route.group);
      expect(["LIVE", "PARTIAL", "NOT_IMPLEMENTED"]).toContain(route.status);
      expect(route.available).toBe(route.status !== "NOT_IMPLEMENTED");
    }
    expect(ROUTES.map((route) => route.id)).toEqual(expect.arrayContaining(["history", "risk", "data", "jobs", "assistant"]));
  });

  it("labels partial and unbuilt modules in the navigation", async () => {
    render(<App fetcher={offline} />);
    await screen.findByRole("alert");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getAllByText("Later").length).toBe(ROUTES.filter((route) => route.status === "NOT_IMPLEMENTED").length);
    expect(within(nav).getAllByText("Partial").length).toBe(ROUTES.filter((route) => route.status === "PARTIAL").length);
  });
});

describe("P10 theme", () => {
  it("switches theme from the header and persists the preference", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<App fetcher={offline} />);
    await screen.findByRole("alert");
    expect(document.documentElement.dataset.theme).toBe("dark");
    await user.click(screen.getByRole("button", { name: "Switch to light theme" }));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("gtf-theme")).toBe("light");
    unmount();
    render(<App fetcher={offline} />);
    await screen.findByRole("alert");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(screen.getByRole("button", { name: "Switch to dark theme" })).toBeInTheDocument();
  });

  it("offers the theme as a setting", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/settings";
    render(<App fetcher={createPlatform().fetcher} />);
    const group = await screen.findByRole("group", { name: "Theme" });
    await user.click(within(group).getByRole("button", { name: "Light" }));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(within(group).getByRole("button", { name: "Light" })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("P10 honest capability states", () => {
  it("Data Health never claims certification when the API says it is not certified", async () => {
    window.location.hash = "#/data";
    render(<App fetcher={createPlatform({ health: { ...healthBase, certified_p0_data: false, readiness_state: "NOT_READY" } }).fetcher} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Data Health" })).toBeInTheDocument();
    expect(await screen.findByText("Not certified")).toBeInTheDocument();
    expect(document.querySelector('[data-provenance="CERTIFIED"]')).toBeNull();
    expect(document.querySelector('[data-provenance="PROVISIONAL"]')).not.toBeNull();
  });

  it("the assistant states that no language model is connected and offers no free-text box", async () => {
    window.location.hash = "#/assistant";
    render(<App fetcher={createPlatform().fetcher} />);
    expect(await screen.findByRole("heading", { level: 1, name: "AI Research Assistant" })).toBeInTheDocument();
    expect(screen.getByText("Language model not connected")).toBeInTheDocument();
    expect(document.querySelector("textarea")).toBeNull();
    expect(screen.getByRole("button", { name: "Why this status?" })).toBeDisabled();
  });

  it("strategy analytics is a capability page without figures", async () => {
    window.location.hash = "#/analytics";
    render(<App fetcher={createPlatform().fetcher} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Strategy Analytics" })).toBeInTheDocument();
    expect(screen.getByText("This module is not available in the current release.")).toBeInTheDocument();
    expect(document.querySelector('[data-provenance="NOT_IMPLEMENTED"]')).not.toBeNull();
    expect(screen.queryByText(/win rate \d/i)).toBeNull();
  });

  it("risk overview keeps sector and drawdown unavailable rather than zero", async () => {
    window.location.hash = "#/risk";
    render(
      <App
        fetcher={
          createPlatform({
            portfolio: {
              trades_triggered_this_month: 2,
              monthly_cap: 10,
              open_positions: 0,
              open_position_cap: 10,
              portfolio_risk_state: "UNAVAILABLE",
              exposure_state: "UNAVAILABLE",
              sector_state: "UNAVAILABLE",
              drawdown_state: "UNAVAILABLE",
              valuation_state: "UNAVAILABLE",
              zones: [],
            },
          }).fetcher
        }
      />,
    );
    expect(await screen.findByText("2 of 10")).toBeInTheDocument();
    expect(screen.getByText("0 of 10")).toBeInTheDocument();
    expect(screen.getAllByText(/— UNAVAILABLE/).length).toBeGreaterThanOrEqual(2);
  });
});

describe("P10 trade plan actions follow the backend", () => {
  it("shows only transitions returned by the plan history route", async () => {
    window.location.hash = "#/plans?plan=plan-1";
    const platform = createPlatform({
      handle: (call) => {
        if (call.path === "/api/v1/plans" && call.method === "GET") return envelope({ plans: [], counts_by_state: { APPROVED: 1 } });
        if (call.path === "/api/v1/plans/plan-1") {
          return envelope({ plan_id: "plan-1", symbol: "SYN", state: "APPROVED", candidate_status: "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING", entry_id: 4, journal_state: "PLANNED", journal_sync: "IN_SYNC" });
        }
        if (call.path === "/api/v1/plans/plan-1/history") {
          return envelope({ plan_id: "plan-1", events: [{ event_id: 1, action: "approve", from_state: "DRAFT", to_state: "APPROVED", actor: "owner", at: "2026-11-17T10:00:00Z" }], allowed_transitions: ["CANCELLED", "EXPIRED"] });
        }
        return null;
      },
    });
    render(<App fetcher={platform.fetcher} />);
    expect(await screen.findByTestId("plan-allowed-transitions")).toHaveTextContent("CANCELLED, EXPIRED");
    expect(screen.queryByRole("button", { name: "Approve plan" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Submit for review" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reject" })).toBeNull();
    expect(screen.getByTestId("cancel-in-journal")).toHaveTextContent("Cancel it in the Journal");
    expect(screen.getByText("approve")).toBeInTheDocument();
  });
});

describe("P10 display formatting", () => {
  it("formats only real numbers and never turns missing values into zero", () => {
    expect(toNumber(null)).toBeNull();
    expect(toNumber("")).toBeNull();
    expect(toNumber("12.5")).toBe(12.5);
    expect(formatInr(null)).toBeNull();
    expect(formatInr("abc")).toBeNull();
    expect(formatInr(1234567.891)).toBe("₹12,34,567.89");
    expect(formatInr(-400)).toBe("−₹400.00");
    expect(formatPaise(12345)).toBe("₹123.45");
    expect(formatPrice(160.44)).toBe("160.44");
    expect(formatQuantity(181)).toBe("181");
    expect(formatDate("2024-02-02T15:30:00")).toBe("2024-02-02 15:30");
    expect(formatDate(undefined)).toBeNull();
  });
});

const healthBase = {
  outcome: "WARNING",
  scheduler_state: "STOPPED",
  database_files: { platform: { configured: true, reachable: true }, research: { configured: false, reachable: false } },
  last_successful_ingest_date: "2024-06-14",
  last_scan_run_id: null,
  last_scan: null,
  last_scan_state: "UNAVAILABLE",
  data_limitations: ["DATA_READY_NOT_CLAIMED"],
  data_ready: false,
  orders_placed: false,
};

describe("P10 independent review regressions", () => {
  it("I-1: a blank price never records a close or a print", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/journal?entry=3";
    const platform = createPlatform({ journal: { entries: [], total: 0, evidence_class: "JOURNAL_DESCRIPTIVE" } });
    render(<App fetcher={platform.fetcher} />);
    await screen.findByRole("heading", { level: 1, name: "Trading Journal" });
    await user.click(await screen.findByText("Close or cancel"));
    await user.click(screen.getByRole("button", { name: "Record close event" }));
    expect(await screen.findByText(/needs the exit price/)).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
    await user.type(screen.getByLabelText("Print quantity"), "10");
    await user.click(screen.getByRole("button", { name: "Record print" }));
    expect(await screen.findByText(/Print price must be a positive number/)).toBeInTheDocument();
    expect(platform.calls.some((call) => call.method === "POST" && call.path.startsWith("/api/v1/journal/"))).toBe(false);
  });

  it("I-2: blank backtest costs are sent as null, never 0", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/backtest";
    const platform = createPlatform({
      handle: (call) => (call.path === "/api/v1/backtests" ? new Response(JSON.stringify({ error: { code: "DATA_INSUFFICIENT", message: "An owner-supplied cost_pct_per_side is required.", details: {} } }), { status: 422 }) : null),
    });
    render(<App fetcher={platform.fetcher} />);
    await user.click(await screen.findByRole("button", { name: "Run labelled study" }));
    expect(await screen.findByText(/owner-supplied cost_pct_per_side is required/)).toBeInTheDocument();
    const body = platform.calls.find((call) => call.path === "/api/v1/backtests")?.body as Record<string, unknown>;
    expect(body.cost_pct_per_side).toBeNull();
    expect(body.slippage_pct_per_side).toBeNull();
  });

  it("I-3: checklist answers do not carry over to another plan", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/plans";
    const plan = (id: string) => ({ plan_id: id, symbol: "SYN", state: "DRAFT", candidate_status: "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING", zone_id: "z" });
    const platform = createPlatform({
      handle: (call) => {
        if (call.path === "/api/v1/plans" && call.method === "GET") return envelope({ plans: [plan("plan-a"), plan("plan-b")], counts_by_state: { DRAFT: 2 } });
        const match = /^\/api\/v1\/plans\/(plan-[ab])(\/history)?$/.exec(call.path);
        if (match) return match[2] ? envelope({ events: [], allowed_transitions: ["APPROVED", "AWAITING_OWNER", "CANCELLED", "REJECTED"] }) : envelope(plan(match[1]));
        return null;
      },
    });
    render(<App fetcher={platform.fetcher} />);
    const openA = await screen.findAllByRole("button", { name: /plan-a/ });
    await user.click(openA[0]);
    await user.selectOptions(await screen.findByLabelText("AUTHENTICITY"), "true");
    expect(screen.getByLabelText("AUTHENTICITY")).toHaveValue("true");
    await user.click(screen.getAllByRole("button", { name: /plan-b/ })[0]);
    expect(await screen.findByText("plan-b", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByLabelText("AUTHENTICITY")).toHaveValue("");
  });

  it("I-4: the assistant does not claim a connection while the API is down", async () => {
    window.location.hash = "#/assistant";
    render(<App fetcher={offline} />);
    await screen.findByRole("alert");
    expect(screen.getByText(/Deterministic explainer unavailable/)).toBeInTheDocument();
    expect(document.querySelector('[data-provenance="LIVE"]')).toBeNull();
  });

  it("I-5: Save is disabled when settings could not be read", async () => {
    window.location.hash = "#/settings";
    const platform = createPlatform({
      handle: (call) => (call.path === "/api/v1/settings" && call.method === "GET" ? new Response(JSON.stringify({ error: { code: "UNAVAILABLE", message: "store locked", details: {} } }), { status: 503 }) : null),
    });
    render(<App fetcher={platform.fetcher} />);
    expect(await screen.findByText(/Settings could not be read/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });
});
