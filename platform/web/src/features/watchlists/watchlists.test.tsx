import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../../app/App";
import { createPlatform, envelope, failure, type Call } from "../../test/platformFetch";
import type { Watchlist } from "../../types/contracts";

function watchPlatform(handle: (call: Call) => Response | null) {
  window.location.hash = "#/watchlists";
  const platform = createPlatform({ handle });
  render(<App fetcher={platform.fetcher} />);
  return platform;
}

describe("watchlists", () => {
  it("shows an empty state", async () => {
    watchPlatform(() => null);
    expect(await screen.findByRole("heading", { level: 1, name: "Watchlists" })).toBeInTheDocument();
    expect(await screen.findByText("No watchlist is stored")).toBeInTheDocument();
  });

  it("creates, renames, searches, reorders, and removes symbols", async () => {
    const user = userEvent.setup();
    let lists: Watchlist[] = [];
    const platform = watchPlatform((call) => {
      if (call.path === "/api/v1/watchlists" && call.method === "GET") return envelope({ watchlists: lists });
      if (call.path === "/api/v1/watchlists" && call.method === "POST") {
        const body = call.body as { name?: string; symbols?: string[] };
        if (!call.headers.get("Idempotency-Key")) return failure(400, "REQUEST_INVALID", "Idempotency-Key is required");
        if (body.name === "Dup") return failure(400, "REQUEST_INVALID", "name is required");
        const created: Watchlist = {
          watchlist_id: "wl-1",
          name: body.name ?? "",
          symbols: body.symbols ?? [],
          eligibility: null,
          note: "Watchlist membership is not a trading signal.",
        };
        lists = [created];
        return envelope(created, 201);
      }
      if (call.path === "/api/v1/watchlists/wl-1" && call.method === "PATCH") {
        const body = call.body as { name?: string; symbols?: string[] };
        lists = lists.map((list) => ({
          ...list,
          name: body.name ?? list.name,
          symbols: body.symbols ?? list.symbols,
        }));
        return envelope(lists[0]);
      }
      if (call.path === "/api/v1/instruments") {
        const params = new URLSearchParams(call.search);
        const query = (params.get("query") ?? "").toUpperCase();
        if (query === "NOPE" || query === "ZZZNO") return envelope({ instruments: [] });
        if (query.includes("RELIANCE") || query === "INE002A01018") {
          return envelope({
            instruments: [{ symbol: "RELIANCE", name: "Reliance Industries", isin: "INE002A01018", verified: false }],
          });
        }
        return envelope({ instruments: [] });
      }
      return null;
    });
    expect(await screen.findByText("No watchlist is stored")).toBeInTheDocument();
    await user.type(screen.getByLabelText("New watchlist"), "   ");
    await user.click(screen.getByRole("button", { name: "Create watchlist" }));
    expect(screen.getByText("name is required")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("New watchlist"));
    await user.type(screen.getByLabelText("New watchlist"), "Dup");
    await user.click(screen.getByRole("button", { name: "Create watchlist" }));
    expect(await screen.findByText(/REQUEST_INVALID: name is required/)).toBeInTheDocument();
    await user.clear(screen.getByLabelText("New watchlist"));
    await user.type(screen.getByLabelText("New watchlist"), "Ideas");
    await user.click(screen.getByRole("button", { name: "Create watchlist" }));
    expect(await screen.findByText("Watchlist membership is not a trading signal.")).toBeInTheDocument();
    expect(platform.calls.some((call) => call.method === "POST" && call.headers.get("Idempotency-Key"))).toBe(true);
    await user.type(screen.getByLabelText("Add symbol"), "NOPE");
    await user.click(screen.getByRole("button", { name: "Search instruments" }));
    expect(await screen.findByText(/No instrument matched/)).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Add symbol"));
    await user.type(screen.getByLabelText("Add symbol"), "Reliance");
    await user.click(screen.getByRole("button", { name: "Search instruments" }));
    expect(await screen.findByText(/Reliance Industries/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Use RELIANCE" }));
    expect(await screen.findByText("INE002A01018")).toBeInTheDocument();
    expect(screen.getByText("false")).toBeInTheDocument();
    const add = screen.getByLabelText("Add symbol");
    await user.clear(add);
    await user.type(add, "ZZZNO");
    expect(add).toHaveValue("ZZZNO");
    await user.click(screen.getByRole("button", { name: "Search instruments" }));
    expect(await screen.findByText(/No instrument matched/)).toBeInTheDocument();
    const rename = screen.getByLabelText("Rename");
    await user.clear(rename);
    await user.type(rename, "Later");
    await user.click(screen.getByRole("button", { name: "Rename" }));
    expect(await screen.findByRole("button", { name: /Later/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Remove RELIANCE");
    await user.click(within(dialog).getByRole("button", { name: "Remove" }));
    expect(await screen.findByText("No symbols")).toBeInTheDocument();
  });

  it("reorders by replacing the stored list and shows a backend error", async () => {
    const user = userEvent.setup();
    let symbols = ["TCS", "INFY"];
    let fail = false;
    watchPlatform((call) => {
      if (call.path === "/api/v1/watchlists" && call.method === "GET") {
        return envelope({
          watchlists: [{ watchlist_id: "wl-2", name: "Book", symbols, eligibility: null, note: "Watchlist membership is not a trading signal." }],
        });
      }
      if (call.path === "/api/v1/watchlists/wl-2" && call.method === "PATCH") {
        if (fail) return failure(409, "CONFLICT", "The list could not be saved");
        symbols = (call.body as { symbols: string[] }).symbols;
        return envelope({ watchlist_id: "wl-2", name: "Book", symbols, eligibility: null, note: "Watchlist membership is not a trading signal." });
      }
      if (call.path === "/api/v1/instruments") return envelope({ instruments: [] });
      return null;
    });
    expect(await screen.findByText("TCS")).toBeInTheDocument();
    const uppers = screen.getAllByRole("button", { name: "Move down" });
    await user.click(uppers[0]);
    await waitFor(() => {
      const body = screen.getAllByRole("row").slice(1).map((row) => row.textContent ?? "");
      expect(body[0]).toContain("INFY");
      expect(body[1]).toContain("TCS");
    });
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    fail = true;
    await user.click(screen.getAllByRole("button", { name: "Move up" })[1]);
    expect(await screen.findByText(/CONFLICT: The list could not be saved/)).toBeInTheDocument();
  });

  it("resumes a create with the same idempotency key", async () => {
    window.sessionStorage.setItem(
      "gtf-watchlist-pending",
      JSON.stringify({ idempotencyKey: "wl-key", name: "Held", symbols: [] }),
    );
    const platform = watchPlatform((call) => {
      if (call.path === "/api/v1/watchlists" && call.method === "GET") return envelope({ watchlists: [] });
      if (call.path === "/api/v1/watchlists" && call.method === "POST") {
        return envelope({ watchlist_id: "wl-held", name: "Held", symbols: [], eligibility: null, note: "Watchlist membership is not a trading signal." }, 200);
      }
      return null;
    });
    expect(await screen.findByText(/Resume uses the same idempotency key/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Resume create" }));
    expect(await screen.findByText("Watchlist membership is not a trading signal.")).toBeInTheDocument();
    const post = platform.calls.find((call) => call.method === "POST" && call.path === "/api/v1/watchlists");
    expect(post?.headers.get("Idempotency-Key")).toBe("wl-key");
  });
});
