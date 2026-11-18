import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../../app/App";
import { createPlatform, envelope, type PlatformOptions } from "../../test/platformFetch";

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

const journalRows = {
  entries: [
    {
      entry_id: 3,
      symbol: "SYN",
      zone_id: "demand-1",
      state: "OPEN",
      planned_entry: 160,
      planned_stop: 150,
      planned_target: 190,
      quantity: 40,
      charges_state: "ABSENT",
      book: {
        executed_entry_quantity: 40,
        open_quantity: 40,
        average_entry_price: 160,
      },
      review: { review_status: "NOT_REVIEWED" },
    },
  ],
  total: 1,
  authorises_order: false,
  evidence_class: "JOURNAL_DESCRIPTIVE",
};

async function openJournal(options?: PlatformOptions) {
  window.location.hash = "#/journal";
  const platform = createPlatform({
    health: connectedHealth,
    journal: journalRows,
    ...options,
  });
  render(<App fetcher={platform.fetcher} />);
  expect(await screen.findByRole("heading", { level: 1, name: "Trading Journal" })).toBeInTheDocument();
  return platform;
}

describe("journal page", () => {
  it("shows filter controls and descriptive performance labels", async () => {
    await openJournal();
    expect(await screen.findByTestId("journal-filters")).toBeInTheDocument();
    expect(screen.getByTestId("journal-result-count")).toHaveTextContent("Showing 1 of 1 stored rows");
    expect(await screen.findByTestId("journal-performance")).toHaveTextContent("JOURNAL_DESCRIPTIVE");
    expect(screen.getByTestId("journal-performance")).toHaveTextContent("Not certified strategy performance");
    expect(screen.getByTestId("journal-row-3")).toHaveTextContent("SYN");
    expect(screen.getByTestId("journal-row-3")).toHaveTextContent("Charges ABSENT");
  });

  it("shows an empty journal without inventing rows", async () => {
    await openJournal({
      journal: { entries: [], total: 0, authorises_order: false, evidence_class: "JOURNAL_DESCRIPTIVE" },
    });
    expect(await screen.findByText("No journal rows")).toBeInTheDocument();
  });

  it("shows no-search-results distinctly from an empty journal", async () => {
    const user = userEvent.setup();
    await openJournal({
      handle: (call) => {
        if (call.path === "/api/v1/journal" && call.method === "GET") {
          if (call.search.includes("symbol=NOPE")) {
            return envelope({
              entries: [],
              total: 0,
              authorises_order: false,
              evidence_class: "JOURNAL_DESCRIPTIVE",
            });
          }
          return envelope(journalRows);
        }
        return null;
      },
    });
    expect(await screen.findByTestId("journal-row-3")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Symbol"), "NOPE");
    await user.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(await screen.findByText("No search results")).toBeInTheDocument();
    expect(screen.queryByText("No journal rows")).not.toBeInTheDocument();
  });

  it("surfaces a failed journal read without inventing rows", async () => {
    const platform = await openJournal({ journal: null });
    expect(await screen.findByText(/journal could not be read/i)).toBeInTheDocument();
    expect(screen.queryByTestId("journal-row-3")).not.toBeInTheDocument();
    expect(platform.calls.some((call) => call.path === "/api/v1/journal")).toBe(true);
  });
});
