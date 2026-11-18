import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../../app/App";
import { envelope, failure, type Call } from "../../test/platformFetch";
import { createPlatform } from "../../test/platformFetch";

const research = {
  schema: "research-pipeline/1",
  as_of: "2024-06-14T15:30:00",
  trade_type: "MIT",
  invocation: "manual",
  dataset_id: "local-dataset",
  completeness: "PARTIAL",
  full_universe_scan: false,
  authorises_order: false,
  limitations: ["UNIVERSE_UNVERIFIED"],
  symbols_not_opened: ["MISSING"],
  methodology: { pipeline_version: "pv-1" },
  ranking: "That order is not a quality ranking.",
  counts: { symbols: 6, candidate_status: { REJECTED: 1 } },
  symbols: [
    {
      symbol: "PASSCO",
      symbol_status: "EVALUATED",
      candidates: [
        {
          candidate_status: "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
          gates: [{ gate: "G8", outcome: "PASS", reasons: ["stored pass"] }],
          deciding_gates: [],
          zone: { tf: "D", overlay_status: "FRESH", proximal: "100.00", distal: "99.00" },
        },
      ],
    },
    {
      symbol: "FAILCO",
      symbol_status: "EVALUATED",
      candidates: [
        {
          candidate_status: "REJECTED",
          gates: [{ gate: "G3", outcome: "FAIL", reasons: ["zone tested"] }],
          deciding_gates: [{ status: "REJECTED", gates: [{ gate: "G3", outcome: "FAIL", reasons: ["zone tested"] }] }],
          zone: { tf: "D", overlay_status: "TESTED" },
        },
      ],
    },
    {
      symbol: "MANCO",
      symbol_status: "EVALUATED",
      candidates: [
        {
          candidate_status: "MANUAL_REVIEW",
          gates: [{ gate: "G5", outcome: "MANUAL", reasons: ["needs review"], manual_review: ["confirm structure"] }],
          deciding_gates: [{ status: "MANUAL_REVIEW", gates: [{ gate: "G5", outcome: "MANUAL", reasons: ["needs review"] }] }],
          zone: { tf: "W", overlay_status: "UNKNOWN" },
        },
      ],
    },
    { symbol: "BLOCKCO", symbol_status: "BLOCKED", reasons: ["M4B_INTRADAY_NOT_APPROVED"], limitations: ["UNIVERSE_UNVERIFIED"], candidates: [] },
    {
      symbol: "DATACO",
      symbol_status: "DATA_INSUFFICIENT",
      reasons: ["NO_COMPLETED_CANDLE_AT_OR_BEFORE_AS_OF"],
      limitations: ["CORPORATE_ACTION_COVERAGE_UNKNOWN"],
      candidates: [],
    },
    { symbol: "GAPCO", candidates: [{ zone: {} }] },
  ],
};

function renderScanner(handle?: (call: Call) => Response | Promise<Response> | null) {
  window.location.hash = "#/scanner";
  const platform = createPlatform({ handle });
  const view = render(<App fetcher={platform.fetcher} />);
  return { ...view, ...platform };
}

describe("stock scanner", () => {
  it("submits a MIT scan with an idempotency key and does not treat HTTP 202 as completion", async () => {
    const user = userEvent.setup();
    let posts = 0;
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const platform = renderScanner((call) => {
      if (call.path === "/api/v1/scans" && call.method === "POST") {
        posts += 1;
        return gate.then(() =>
          envelope({ job_id: "job-1", state: "RUNNING", completeness: null, progress: { done: 1, total: 4, unit: "symbols" }, result_ref: null }, 202),
        );
      }
      if (call.path === "/api/v1/jobs/job-1") {
        return envelope({ job_id: "job-1", state: "RUNNING", completeness: null, progress: { done: 1, total: 4, unit: "symbols" }, result_ref: null });
      }
      return null;
    });
    expect(await screen.findByRole("option", { name: "local-dataset" })).toBeInTheDocument();
    const pending = user.click(screen.getByRole("button", { name: "Run scan" }));
    expect(await screen.findByRole("button", { name: "Submitting" })).toBeDisabled();
    expect(posts).toBe(1);
    release();
    await pending;
    expect(posts).toBe(1);
    const post = platform.calls.find((call) => call.path === "/api/v1/scans" && call.method === "POST");
    expect(post?.headers.get("Idempotency-Key")).toBeTruthy();
    expect(post?.headers.get("X-GTF-Request")).toBe("1");
    expect((post?.body as { trade_type: string }).trade_type).toBe("MIT");
    expect(post?.body).not.toHaveProperty("max_base_candles");
    expect(await screen.findByText(/Accepted \(HTTP 202\)/)).toBeInTheDocument();
    expect(screen.getByText("1 of 4 symbols")).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByText("SUCCEEDED_COMPLETE")).not.toBeInTheDocument();
  });

  it("shows WIT-75 and WIT-125 blocked results from the engine", async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem("gtf-poll-ms", "20");
    const wit = {
      ...research,
      trade_type: "WIT-75",
      completeness: "COMPLETE",
      limitations: ["FIXTURE_NOT_MARKET_DATA"],
      symbols: [{ symbol: "FIX", symbol_status: "BLOCKED", reasons: ["M4B_INTRADAY_NOT_APPROVED"], candidates: [] }],
    };
    const platform = renderScanner((call) => {
      if (call.path === "/api/v1/scans" && call.method === "POST") {
        return envelope({ job_id: "job-wit", state: "RUNNING", completeness: null, progress: null, result_ref: null }, 202, true);
      }
      if (call.path === "/api/v1/jobs/job-wit") {
        return envelope({ job_id: "job-wit", state: "SUCCEEDED_COMPLETE", completeness: "COMPLETE", progress: null, result_ref: "scan-wit" }, 200, true);
      }
      if (call.path === "/api/v1/scans/scan-wit") return envelope(wit, 200, true);
      if (call.path === "/api/v1/scans/scan-wit/symbols") return envelope({ scan_key: "scan-wit", symbols: wit.symbols }, 200, true);
      return null;
    });
    expect(await screen.findByRole("option", { name: "local-dataset" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Trade type"), "WIT-75");
    await user.click(screen.getByRole("button", { name: "Run scan" }));
    expect(await screen.findByText("M4B_INTRADAY_NOT_APPROVED")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
    expect(screen.getAllByText("FIXTURE_NOT_MARKET_DATA").length).toBeGreaterThan(0);
    expect(screen.queryByText("Pass")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Trade type"), "WIT-125");
    await user.click(screen.getByRole("button", { name: "Run scan" }));
    await waitFor(() => {
      const posted = platform.calls.filter((call) => call.path === "/api/v1/scans" && call.method === "POST");
      expect(posted.map((call) => (call.body as { trade_type: string }).trade_type)).toEqual(["WIT-75", "WIT-125"]);
    });
  });

  it("polls until a terminal state, cancels only when the backend confirms it, and stops on unmount", async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem("gtf-poll-ms", "20");
    let jobState = "RUNNING";
    let jobGets = 0;
    const platform = renderScanner((call) => {
      if (call.path === "/api/v1/scans" && call.method === "POST") {
        return envelope({ job_id: "job-c", state: "RUNNING", completeness: null, progress: null, result_ref: null }, 202);
      }
      if (call.path === "/api/v1/scans/job-c/cancel" && call.method === "POST") {
        expect(call.headers.get("Idempotency-Key")).toBeTruthy();
        return envelope({ job_id: "job-c", state: "RUNNING", completeness: null, progress: null, result_ref: null }, 202);
      }
      if (call.path === "/api/v1/jobs/job-c") {
        jobGets += 1;
        return envelope({ job_id: "job-c", state: jobState, completeness: jobState === "CANCELLED" ? null : null, progress: null, result_ref: null });
      }
      return null;
    });
    expect(await screen.findByRole("option", { name: "local-dataset" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run scan" }));
    expect(await screen.findByText("Cancel job")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel job" }));
    expect(await screen.findByText(/The job state is still RUNNING/)).toBeInTheDocument();
    expect(screen.queryByText("CANCELLED")).not.toBeInTheDocument();
    jobState = "CANCELLED";
    expect(await screen.findByText("CANCELLED")).toBeInTheDocument();
    const seen = jobGets;
    platform.unmount();
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(jobGets - seen).toBeLessThanOrEqual(1);
  });

  it("shows an interrupted job as interrupted", async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem("gtf-poll-ms", "20");
    renderScanner((call) => {
      if (call.path === "/api/v1/scans" && call.method === "POST") {
        return envelope({ job_id: "job-i", state: "VALIDATING", completeness: null, progress: null, result_ref: null }, 202);
      }
      if (call.path === "/api/v1/jobs/job-i") {
        return envelope({ job_id: "job-i", state: "INTERRUPTED", completeness: null, progress: null, result_ref: null, error: { code: "INTERRUPTED", message: "Heartbeat stopped" } });
      }
      return null;
    });
    expect(await screen.findByRole("option", { name: "local-dataset" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run scan" }));
    expect(await screen.findByText(/Heartbeat stopped/)).toBeInTheDocument();
    expect(screen.getAllByText(/INTERRUPTED/).length).toBeGreaterThan(0);
    expect(screen.queryByText("SUCCEEDED_COMPLETE")).not.toBeInTheDocument();
  });

  it("restores a stored job without posting again", async () => {
    window.sessionStorage.setItem("gtf-scan-pending", JSON.stringify({ idempotencyKey: "kept", body: { mode: "MANUAL" }, jobId: "job-restored" }));
    const platform = renderScanner((call) => {
      if (call.path === "/api/v1/jobs/job-restored") {
        return envelope({ job_id: "job-restored", state: "SUCCEEDED_PARTIAL", completeness: "PARTIAL", progress: null, result_ref: "scan-restored" });
      }
      if (call.path === "/api/v1/scans/scan-restored") {
        return envelope({ ...research, completeness: "PARTIAL", symbols: [] });
      }
      if (call.path === "/api/v1/scans/scan-restored/symbols") return envelope({ symbols: [] });
      return null;
    });
    expect(await screen.findByText(/Restored the stored job/)).toBeInTheDocument();
    expect(await screen.findByText("SUCCEEDED_PARTIAL")).toBeInTheDocument();
    expect(platform.calls.some((call) => call.path === "/api/v1/scans" && call.method === "POST")).toBe(false);
  });

  it("renders stored statuses, missing fields, history, and symbol evidence", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/scanner?scan=scan-1";
    const platform = createPlatform({
      scans: [
        { scan_key: "scan-real", as_of: "2024-06-14", trade_type: "MIT", completeness: "FAILED", dataset_id: "local-dataset", fixture: false },
        { scan_key: "scan-fix", as_of: "2024-06-14", trade_type: "MIT", completeness: "COMPLETE", dataset_id: "fixture", fixture: true },
      ],
      handle: (call) => {
        if (call.path === "/api/v1/scans/scan-1") return envelope(research);
        if (call.path === "/api/v1/scans/scan-1/symbols") return envelope({ scan_key: "scan-1", symbols: research.symbols });
        if (call.path === "/api/v1/symbols/DATACO/bundle") {
          return envelope({
            scan_key: "scan-1",
            dataset_id: "local-dataset",
            as_of: research.as_of,
            trade_type: "MIT",
            authorises_order: false,
            stored: research.symbols[4],
          });
        }
        if (call.path === "/api/v1/candles") {
          return envelope({
            symbol: "DATACO",
            timeframe: "D",
            dataset_id: "local-dataset",
            available_from: "2024-06-03",
            available_to: "2024-06-14",
            limitations: ["NO_BARS"],
            missing_sessions: ["2024-06-10"],
            volume_state: "UNAVAILABLE",
            adjusted: false,
            candles: [{ session_date: "2024-06-14", open: "101.50", high: "102.00", low: "100.00", close: "101.00", volume: null }],
          });
        }
        return null;
      },
    });
    render(<App fetcher={platform.fetcher} />);
    expect(await screen.findByText("PASSCO")).toBeInTheDocument();
    for (const code of ["REJECTED", "MANUAL_REVIEW", "BLOCKED", "DATA_INSUFFICIENT", "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING"]) {
      expect(document.querySelector(`[data-status="${code}"]`), code).toBeTruthy();
    }
    const table = screen.getAllByRole("table").find((node) => within(node).queryByText("Deciding gates")) as HTMLElement;
    expect(within(table).getByText(/G3 FAIL/)).toBeInTheDocument();
    expect(within(table).getByText(/G5 MANUAL/)).toBeInTheDocument();
    // P3-D: the stored outcome panel names the stored reason classes for this partial scan.
    const outcome = screen.getByTestId("scan-outcome");
    expect(outcome).toHaveAttribute("data-kind", "QUALIFIED");
    expect(within(outcome).getByText(/G3 FAIL/)).toBeInTheDocument();
    expect(outcome.querySelector('[data-code="PARTIAL_SCAN"]')).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Inspect PASSCO" }));
    expect(await screen.findByText("stored pass")).toBeInTheDocument();
    expect(document.querySelector('[data-status="PASS"]')).toBeTruthy();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.getByText("PARTIAL")).toBeInTheDocument();
    expect(screen.getByText("full_universe_scan").parentElement).toHaveTextContent("false");
    expect(screen.getByText("authorises_order").parentElement).toHaveTextContent("false");
    await user.selectOptions(screen.getByLabelText("Decision status"), "FAIL");
    expect(screen.queryByRole("button", { name: "Inspect PASSCO" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inspect FAILCO" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.click(screen.getByRole("button", { name: "Inspect DATACO" }));
    expect(await screen.findByText("101.50")).toBeInTheDocument();
    expect(screen.getByText(/Not a live price/)).toBeInTheDocument();
    expect(screen.getByText(/Missing sessions: 1/)).toBeInTheDocument();
    expect(screen.getByText("scan-real")).toBeInTheDocument();
    expect(screen.queryByText("scan-fix")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show fixture scans" }));
    expect(await screen.findByText("scan-fix")).toBeInTheDocument();
    expect(screen.getAllByText("FIXTURE_NOT_MARKET_DATA").length).toBeGreaterThan(0);
    expect(platform.calls.some((call) => call.path === "/api/v1/symbols/DATACO/bundle")).toBe(true);
    expect(platform.calls.some((call) => call.path === "/api/v1/candles")).toBe(true);
  });

  it("reports session expiry and a validation error", async () => {
    const user = userEvent.setup();
    renderScanner((call) => {
      if (call.path === "/api/v1/scans" && call.method === "POST") return failure(401, "UNAUTHENTICATED", "Session is missing or expired");
      if (call.path === "/api/v1/session/bootstrap") return failure(401, "UNAUTHENTICATED", "Session is missing or expired");
      return null;
    });
    expect(await screen.findByRole("option", { name: "local-dataset" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run scan" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Authentication required");
    expect(screen.getByText(/UNAUTHENTICATED: Session is missing or expired/)).toBeInTheDocument();
  });
});
