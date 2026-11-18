import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../../app/App";
import { createPlatform, failure, type PlatformOptions } from "../../test/platformFetch";

const connectedHealth = {
  outcome: "OK",
  scheduler_state: "STOPPED",
  database_files: {
    platform: { configured: true, reachable: true },
    research: { configured: true, reachable: true },
  },
  last_successful_ingest_date: "2024-06-14",
  last_scan_run_id: "scan-ok",
  last_scan: { scan_key: "scan-ok", as_of: "2024-06-14T15:30:00", completeness: "COMPLETE", dataset_id: "local-dataset" },
  last_scan_state: "COMPLETE",
  data_limitations: ["DATA_READY_NOT_CLAIMED", "UNIVERSE_UNVERIFIED"],
  data_ready: false,
  orders_placed: false,
};

const openBook = {
  trades_triggered_this_month: 3,
  monthly_cap: 10,
  open_positions: 1,
  open_position_cap: 10,
  valuation: 12550,
  valuation_state: "STALE",
  valuation_reason: "Latest accepted close is 2024-06-13; valuation date is 2024-06-14",
  unrealised_pnl: 150,
  exposure: 12550,
  exposure_state: "AVAILABLE",
  portfolio_risk: 400,
  portfolio_risk_state: "AVAILABLE",
  sector: null,
  sector_state: "UNAVAILABLE",
  drawdown: null,
  drawdown_state: "UNAVAILABLE",
  research_use: "FIXTURE_NOT_MARKET_DATA",
  authorises_order: false,
  note: "Counts come from the research journal only. EOD marks are not live quotes.",
  zones: [
    {
      entry_id: 7,
      symbol: "SYN",
      zone_id: "demand-1",
      state: "OPEN",
      counts_as_open: true,
      open_quantity: 40,
      average_entry_price: 160,
      planned_stop: 150,
      locked_stop: 150,
      planned_target: 190,
      realised_pnl: null,
      unrealised_pnl: 150,
      position_risk: 400,
      position_risk_state: "AVAILABLE",
      reason: "TRIGGERED",
      valuation: 163.75,
      valuation_state: "STALE",
      price_date: "2024-06-13",
    },
  ],
};

async function openPortfolio(options?: PlatformOptions) {
  window.location.hash = "#/portfolio";
  const platform = createPlatform({
    health: connectedHealth,
    ...options,
  });
  render(<App fetcher={platform.fetcher} />);
  expect(await screen.findByRole("heading", { level: 1, name: "Portfolio" })).toBeInTheDocument();
  return platform;
}

describe("portfolio page", () => {
  it("shows monthly allowance separately from open-position allowance", async () => {
    await openPortfolio({ portfolio: openBook });
    expect(await screen.findByTestId("portfolio-monthly-count")).toHaveTextContent("3");
    expect(screen.getByTestId("portfolio-monthly-cap")).toHaveTextContent("10");
    expect(screen.getByTestId("portfolio-open-count")).toHaveTextContent("1");
    expect(screen.getByTestId("portfolio-open-cap")).toHaveTextContent("10");
    expect(screen.getByText("Trades this month")).toBeInTheDocument();
    expect(screen.getByText("Open positions")).toBeInTheDocument();
  });

  it("renders open quantity, average entry and position risk from the API payload", async () => {
    const platform = await openPortfolio({ portfolio: openBook });
    expect(await screen.findByTestId("portfolio-open-qty-SYN")).toHaveTextContent("40");
    expect(screen.getByTestId("portfolio-avg-entry-SYN")).toHaveTextContent("160");
    expect(screen.getByTestId("portfolio-position-risk-SYN")).toHaveTextContent("400");
    expect(screen.getByTestId("portfolio-open-risk")).toHaveTextContent("400");
    const portfolioCalls = platform.calls.filter((call) => call.path === "/api/v1/portfolio");
    expect(portfolioCalls.length).toBeGreaterThan(0);
    // UI must display API counters, not invent a second monthly/open calculation.
    expect(screen.getByTestId("portfolio-monthly-count")).toHaveTextContent(String(openBook.trades_triggered_this_month));
    expect(screen.getByTestId("portfolio-open-count")).toHaveTextContent(String(openBook.open_positions));
  });

  it("keeps sector and live drawdown UNAVAILABLE and never shows them as zero", async () => {
    await openPortfolio({ portfolio: openBook });
    expect(await screen.findByTestId("portfolio-sector")).toHaveTextContent("UNAVAILABLE");
    expect(screen.getByTestId("portfolio-drawdown")).toHaveTextContent("UNAVAILABLE");
    expect(screen.getByTestId("portfolio-sector")).not.toHaveTextContent("0");
    expect(screen.getByTestId("portfolio-drawdown")).not.toHaveTextContent("0");
  });

  it("shows STALE mark state, EOD price date and research use", async () => {
    await openPortfolio({ portfolio: openBook });
    expect(await screen.findByTestId("portfolio-valuation-state")).toHaveTextContent("STALE");
    expect(screen.getByTestId("portfolio-mark-state-SYN")).toHaveTextContent("STALE");
    expect(screen.getByTestId("portfolio-price-date-SYN")).toHaveTextContent("2024-06-13");
    expect(screen.getByTestId("portfolio-research-use")).toHaveTextContent("FIXTURE_NOT_MARKET_DATA");
    expect(screen.getByTestId("portfolio-valuation-reason")).toHaveTextContent("2024-06-13");
    expect(screen.getAllByText(/Not a live quote/i).length).toBeGreaterThan(0);
  });

  it("shows an empty open-position state without inventing a zero sector value", async () => {
    await openPortfolio({
      portfolio: {
        ...openBook,
        open_positions: 0,
        valuation: null,
        valuation_state: "UNAVAILABLE",
        unrealised_pnl: "UNAVAILABLE",
        exposure: null,
        exposure_state: "UNAVAILABLE",
        portfolio_risk: null,
        portfolio_risk_state: "UNAVAILABLE",
        zones: [
          {
            entry_id: 8,
            symbol: "SYN",
            zone_id: "demand-1",
            state: "CLOSED",
            counts_as_open: false,
            open_quantity: 0,
            average_entry_price: 160,
            valuation_state: "UNAVAILABLE",
            price_date: null,
            reason: "TRIGGERED",
          },
        ],
      },
    });
    expect(await screen.findByTestId("portfolio-empty-open")).toHaveTextContent("No open journal position");
    expect(screen.getByTestId("portfolio-empty-open")).toHaveTextContent("Refused journal operations are not shown as open positions");
    expect(screen.getByTestId("portfolio-sector")).toHaveTextContent("UNAVAILABLE");
    expect(screen.getByTestId("portfolio-open-count")).toHaveTextContent("0");
  });

  it("surfaces a refused portfolio read without treating it as success", async () => {
    await openPortfolio({ portfolio: null });
    expect(await screen.findByText("Portfolio unavailable")).toBeInTheDocument();
    expect(screen.getByText(/ONE_ORDER_PER_ZONE/)).toBeInTheDocument();
    expect(screen.queryByTestId("portfolio-monthly-count")).not.toBeInTheDocument();
  });

  it("shows a disconnected empty state and does not keep prior counts", async () => {
    window.location.hash = "#/portfolio";
    const offline = (async () => {
      throw new TypeError("offline");
    }) as typeof fetch;
    render(<App fetcher={offline} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Portfolio" })).toBeInTheDocument();
    expect(screen.getByText("The API session is not authenticated. Counts from a previous session are not shown.")).toBeInTheDocument();
    expect(screen.queryByTestId("portfolio-monthly-count")).not.toBeInTheDocument();
  });

  it("shows a loading state before the journal payload arrives", async () => {
    let release!: (value: Response) => void;
    const deferred = new Promise<Response>((resolve) => {
      release = resolve;
    });
    window.location.hash = "#/portfolio";
    const platform = createPlatform({
      health: connectedHealth,
      handle: (call) => {
        if (call.path === "/api/v1/portfolio") {
          return deferred;
        }
        return null;
      },
    });
    render(<App fetcher={platform.fetcher} />);
    expect(await screen.findByText("Loading portfolio")).toBeInTheDocument();
    release(
      new Response(
        JSON.stringify({
          platform_schema: "gtf-platform/1",
          data: openBook,
          meta: { fixture: false },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    await waitFor(() => expect(screen.getByTestId("portfolio-monthly-count")).toHaveTextContent("3"));
  });

  it("keeps UNAVAILABLE valuation from being displayed as zero", async () => {
    await openPortfolio({
      portfolio: {
        ...openBook,
        valuation: null,
        valuation_state: "UNAVAILABLE",
        unrealised_pnl: "UNAVAILABLE",
        exposure: null,
        exposure_state: "UNAVAILABLE",
      },
    });
    expect(await screen.findByTestId("portfolio-valuation")).toHaveTextContent("UNAVAILABLE");
    expect(screen.getByTestId("portfolio-valuation")).not.toHaveTextContent("0");
    expect(screen.getByTestId("portfolio-unrealised")).toHaveTextContent("UNAVAILABLE");
    expect(screen.getByTestId("portfolio-exposure")).toHaveTextContent("UNAVAILABLE");
  });

  it("renders a generic API failure message on the Portfolio page", async () => {
    await openPortfolio({
      handle: (call) => (call.path === "/api/v1/portfolio" ? failure(500, "INTERNAL", "The journal could not be read") : null),
    });
    expect(await screen.findByText("The journal could not be read")).toBeInTheDocument();
    expect(screen.getByText("Portfolio unavailable")).toBeInTheDocument();
    expect(screen.queryByTestId("portfolio-monthly-count")).not.toBeInTheDocument();
  });
});
