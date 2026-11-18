import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../../app/App";
import { createPlatform, failure, type PlatformOptions } from "../../test/platformFetch";

async function openOverview(options?: PlatformOptions) {
  window.location.hash = "#/overview";
  const platform = createPlatform(options);
  render(<App fetcher={platform.fetcher} />);
  expect(await screen.findByRole("heading", { level: 1, name: "Market Overview" })).toBeInTheDocument();
  return platform;
}

describe("overview dashboard", () => {
  it("shows a successful health payload without claiming data_ready", async () => {
    await openOverview({
      health: {
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
      },
    });
    expect(await screen.findByText("data_ready is false. DATA_READY is not claimed.")).toBeInTheDocument();
    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("Authenticated")).toBeInTheDocument();
    expect(screen.getAllByText("scan-ok").length).toBeGreaterThan(0);
    expect(screen.getAllByText("UNIVERSE_UNVERIFIED").length).toBeGreaterThan(0);
    expect(screen.getByTestId("index-value")).toHaveTextContent("Unavailable");
    expect(screen.getByTestId("index-value")).not.toHaveTextContent("0");
  });

  it("shows the API as unavailable when health fails", async () => {
    const platform = createPlatform({
      handle: (call) => (call.path === "/api/v1/health" ? failure(503, "INTERNAL", "The request failed") : null),
    });
    render(<App fetcher={platform.fetcher} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("API unavailable");
    expect(screen.getByRole("alert")).toHaveTextContent("INTERNAL");
  });

  it("does not turn a missing scan into zero counts", async () => {
    await openOverview();
    expect(await screen.findByText("No non-fixture scan is stored")).toBeInTheDocument();
    expect(screen.getByLabelText("DATA_INSUFFICIENT candidate count")).toHaveAttribute("data-count", "unavailable");
    expect(screen.getByLabelText("DATA_INSUFFICIENT candidate count")).not.toHaveTextContent("0");
  });

  it("keeps an omitted status unavailable", async () => {
    await openOverview({
      overview: {
        state: "COMPLETE",
        counts: { symbols: 2, candidate_status: { REJECTED: 2 } },
        index: null,
        sector: null,
        breadth: null,
      },
    });
    expect(await screen.findByLabelText("DATA_INSUFFICIENT candidate count")).toHaveAttribute("data-count", "unavailable");
  });

  it("labels a partial scan and a failed scan", async () => {
    const partial = createPlatform({
      health: {
        outcome: "OK",
        scheduler_state: "STOPPED",
        database_files: {
          platform: { configured: true, reachable: true },
          research: { configured: true, reachable: true },
        },
        last_successful_ingest_date: "2024-06-14",
        last_scan_run_id: "scan-part",
        last_scan: { scan_key: "scan-part", as_of: "2024-06-14", completeness: "PARTIAL", dataset_id: "local-dataset" },
        last_scan_state: "PARTIAL",
        data_limitations: ["UNIVERSE_UNVERIFIED"],
        data_ready: false,
        orders_placed: false,
      },
    });
    window.location.hash = "#/overview";
    render(<App fetcher={partial.fetcher} />);
    expect(await screen.findByText("This scan is PARTIAL. It is not a complete scan.")).toBeInTheDocument();
    expect(screen.queryByText("SUCCEEDED_COMPLETE")).not.toBeInTheDocument();
  });

  it("shows running job phase and derived readiness without claiming data_ready", async () => {
    await openOverview({
      health: {
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
        data_limitations: ["DATA_READY_NOT_CLAIMED"],
        data_ready: false,
        readiness_state: "NOT_READY",
        certified_p0_data: false,
        orders_placed: false,
      },
      overview: {
        state: "COMPLETE",
        counts: { symbols: 1, candidate_status: { ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING: 1 } },
        job: { job_id: "job-stored", state: "SUCCEEDED_COMPLETE" },
        active_job: { job_id: "job-running", state: "RUNNING" },
        job_phase: "RUNNING",
        scan_due: { state: "NOT_READY", as_of: null, reason: "Scheduler is not enabled" },
        readiness_state: "NOT_READY",
        data_ready: false,
        certified_p0_data: false,
        index: null,
        sector: null,
        breadth: null,
      },
    });
    expect(await screen.findByText("data_ready is false. DATA_READY is not claimed.")).toBeInTheDocument();
    expect(screen.getAllByText("NOT_READY").length).toBeGreaterThan(0);
    expect(screen.getByText("A job is RUNNING. It is not a completed scan.")).toBeInTheDocument();
    expect(screen.getByText("Scheduler is not enabled", { exact: false })).toBeInTheDocument();
  });

  it("does not present a failed scan as successful", async () => {
    const platform = createPlatform({
      health: {
        outcome: "WARNING",
        scheduler_state: "STOPPED",
        database_files: {
          platform: { configured: true, reachable: true },
          research: { configured: true, reachable: true },
        },
        last_successful_ingest_date: "2024-06-14",
        last_scan_run_id: "scan-fail",
        last_scan: { scan_key: "scan-fail", as_of: "2024-06-14", completeness: "FAILED", dataset_id: "local-dataset" },
        last_scan_state: "FAILED",
        data_limitations: [],
        data_ready: false,
        orders_placed: false,
      },
    });
    window.location.hash = "#/overview";
    render(<App fetcher={platform.fetcher} />);
    expect(await screen.findByText("This scan FAILED. It is not a successful scan.")).toBeInTheDocument();
    expect(screen.getByText("Latest successful scan").parentElement).toHaveTextContent("Unavailable");
  });

  it("shows a missing dataset and an empty watchlist", async () => {
    await openOverview({ datasets: [], watchlists: [] });
    expect(await screen.findByText("No dataset")).toBeInTheDocument();
    expect(await screen.findByText("No watchlist is stored")).toBeInTheDocument();
  });

  it("keeps fixture scans out of the accepted activity until requested", async () => {
    const user = userEvent.setup();
    const platform = await openOverview({
      scans: [
        { scan_key: "scan-real", as_of: "2024-06-14", trade_type: "MIT", completeness: "COMPLETE", dataset_id: "local-dataset", fixture: false },
        { scan_key: "scan-fix", as_of: "2024-06-14", trade_type: "MIT", completeness: "COMPLETE", dataset_id: "fixture-dataset", fixture: true },
      ],
    });
    expect(await screen.findByText("scan-real")).toBeInTheDocument();
    expect(screen.queryByText("scan-fix")).not.toBeInTheDocument();
    expect(platform.calls.filter((call) => call.path === "/api/v1/scans").every((call) => !call.search.includes("include_fixtures=true"))).toBe(true);
    await user.click(screen.getByRole("button", { name: "Show fixture scans" }));
    expect(await screen.findByText("scan-fix")).toBeInTheDocument();
    expect(screen.getAllByText("FIXTURE_NOT_MARKET_DATA").length).toBeGreaterThan(0);
    expect(screen.getByText("scan-real")).toBeInTheDocument();
  });
});
