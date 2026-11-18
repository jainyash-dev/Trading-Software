import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { ROUTES } from "../navigation/routes";

const offline = (async () => {
  throw new TypeError("offline");
}) as typeof fetch;

describe("application shell", () => {
  it("shows a disconnected API and keeps fixture data behind an explicit control", async () => {
    const user = userEvent.setup();
    render(<App fetcher={offline} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("API disconnected");
    expect(screen.queryByText("FIXTURE_NOT_MARKET_DATA")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^buy$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^sell$/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show fixture specimens" }));
    expect(screen.getByText("FIXTURE_NOT_MARKET_DATA")).toBeInTheDocument();
  });

  it("navigates to every destination and marks the active item", async () => {
    const user = userEvent.setup();
    render(<App fetcher={offline} />);
    await screen.findByRole("alert");
    for (const route of ROUTES) {
      await user.click(screen.getByRole("link", { name: route.label }));
      expect(screen.getByRole("link", { name: route.label })).toHaveAttribute("aria-current", "page");
      expect(screen.getByRole("heading", { level: 1, name: new RegExp(route.label.replace("/", "\\/"), "i") })).toBeInTheDocument();
    }
  });

  it("opens a stored route from the address bar and can compact the navigation", async () => {
    window.location.hash = "#/watchlists";
    render(<App fetcher={offline} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Watchlists" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Watchlists" })).toHaveAttribute("aria-current", "page");
  });

  it("labels later modules and keeps them reachable when the navigation is compact", async () => {
    const user = userEvent.setup();
    window.matchMedia = ((query: string) => ({
      matches: query.includes("1100"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
      onchange: null,
    })) as typeof window.matchMedia;
    render(<App fetcher={offline} />);
    await screen.findByRole("alert");
    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveAttribute("data-compact", "true");
    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(screen.getByRole("link", { name: "Shadow / Paper" })).toHaveAttribute("title", "Shadow / Paper. Not available yet");
    await user.click(screen.getByRole("link", { name: "Stock Analysis" }));
    expect(screen.queryByText("This module is not available in the current release.")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Stock Analysis" })).toBeInTheDocument();
  });

  it("does not reopen the session on every render", async () => {
    const original = window.fetch;
    const calls: string[] = [];
    window.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      const data = url.includes("/health")
        ? {
            outcome: "WARNING",
            scheduler_state: "STOPPED",
            database_files: {
              platform: { configured: true, reachable: true },
              research: { configured: false, reachable: false },
            },
            last_successful_ingest_date: null,
            last_scan_run_id: null,
            last_scan: null,
            last_scan_state: "UNAVAILABLE",
            data_limitations: ["DATA_READY_NOT_CLAIMED"],
            data_ready: false,
            orders_placed: false,
          }
        : url.includes("/datasets")
          ? { datasets: [], limitations: ["DATA_READY_NOT_CLAIMED"] }
          : url.includes("/scans")
            ? { scans: [], next_cursor: null }
            : url.includes("/watchlists")
              ? { watchlists: [] }
              : { authenticated: true, auth: "cookie" };
      return new Response(
        JSON.stringify({ platform_schema: "gtf-platform/1", data, meta: { fixture: false } }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }) as typeof fetch;
    try {
      render(<App />);
      expect(await screen.findByText("data_ready is false. DATA_READY is not claimed.")).toBeInTheDocument();
      const sessions = () => calls.filter((url) => url.includes("/session")).length;
      const settled = sessions();
      await new Promise((resolve) => setTimeout(resolve, 200));
      expect(sessions()).toBe(settled);
      expect(settled).toBeLessThan(4);
    } finally {
      window.fetch = original;
    }
  });

  it("focuses search with slash and does not treat an unknown status as pass", async () => {
    const user = userEvent.setup();
    render(<App fetcher={offline} />);
    await screen.findByRole("alert");
    await user.keyboard("/");
    expect(document.activeElement).toBe(document.getElementById("global-search"));
    await user.click(screen.getByRole("button", { name: "Show fixture specimens" }));
    await user.click(screen.getByRole("link", { name: "Settings" }));
    expect(screen.getByText("Unknown status: NOT_A_REAL_STATUS")).toBeInTheDocument();
    expect(screen.getByText("Unknown status: NOT_A_REAL_STATUS").textContent?.toLowerCase()).not.toContain("pass");
  });
});
