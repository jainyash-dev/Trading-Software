import { useEffect, useRef, useState } from "react";
import { useAppState } from "../state/store";
import type { Instrument } from "../types/contracts";
import { Icon } from "./icons";

function asInstrument(value: unknown): Instrument | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  if (typeof row.symbol !== "string" || !row.symbol.trim()) return null;
  return {
    symbol: row.symbol,
    name: typeof row.name === "string" && row.name.trim() ? row.name : null,
    isin: typeof row.isin === "string" && row.isin.trim() ? row.isin : null,
    verified: row.verified === true,
  };
}

export function InstrumentSearch() {
  const app = useAppState();
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<Instrument[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const box = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const onDown = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) {
        setRows(null);
        setMessage(null);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  async function search() {
    const text = query.trim();
    if (app.connection !== "connected") {
      setRows(null);
      setMessage(app.connection === "unauthenticated" ? "Authentication required" : "API required");
      return;
    }
    if (!text) {
      setRows(null);
      setMessage("Enter a symbol, name, or ISIN.");
      return;
    }
    const result = await app.request<{ instruments?: unknown[] }>("/api/v1/instruments", { query: { query: text } });
    if (!result.ok) {
      app.reportFailure(result);
      setRows(null);
      setMessage(`${result.error.code}: ${result.error.message}`);
      return;
    }
    const instruments = (result.envelope.data.instruments ?? []).map(asInstrument).filter((item): item is Instrument => item !== null);
    setRows(instruments);
    setMessage(instruments.length === 0 ? "No instrument matched." : null);
  }

  return (
    <form
      ref={box}
      role="search"
      className="relative"
      onSubmit={(event) => {
        event.preventDefault();
        void search();
      }}
    >
      <label htmlFor="global-search" className="sr-only">
        Search
      </label>
      <div className="flex h-8 items-center gap-1.5 rounded-[4px] border border-line-strong bg-surface pl-2 pr-1 focus-within:border-[var(--gtf-focus)]">
        <Icon name="search" size={14} className="text-muted" />
        <input
          id="global-search"
          value={query}
          aria-label="Search instruments"
          placeholder={app.connection === "connected" ? "Search symbol, name, ISIN" : "Search needs the API"}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setRows(null);
              setMessage(null);
            }
          }}
          className="h-full w-44 min-w-0 border-0 bg-transparent text-[12.5px] outline-none placeholder:text-muted xl:w-56"
        />
        <kbd className="hidden rounded-[3px] border border-line px-1 text-[10px] text-muted sm:inline">/</kbd>
        <button
          type="submit"
          disabled={app.connection !== "connected"}
          className="h-6 rounded-[3px] px-2 text-[11.5px] font-medium text-ink-2 hover:bg-surface-2 disabled:opacity-40"
        >
          Find
        </button>
      </div>
      {message ? (
        <p className="absolute right-0 z-30 mt-1 w-72 rounded-[4px] border border-line bg-elevated px-3 py-2 text-[12px] shadow-[var(--gtf-shadow-lg)]" role="status">
          {message}
        </p>
      ) : null}
      {rows && rows.length > 0 ? (
        <ul
          className="scroll-thin absolute right-0 z-30 mt-1 max-h-96 w-[22rem] overflow-auto rounded-[4px] border border-line bg-elevated text-[12px] shadow-[var(--gtf-shadow-lg)]"
          aria-label="Instrument results"
        >
          {rows.map((row) => (
            <li key={`${row.symbol}-${row.isin ?? ""}`} className="border-b border-line px-3 py-2 last:border-b-0">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-semibold">{row.symbol}</span>
                <span className={`text-[10.5px] ${row.verified ? "text-[var(--gtf-ok)]" : "text-[var(--gtf-manual)]"}`}>
                  identity {row.verified ? "verified" : "unverified"}
                </span>
              </div>
              <p className="truncate text-muted">{row.name ?? "Name unavailable"}</p>
              <p className="code text-muted">ISIN {row.isin ?? "unavailable"}</p>
              <div className="mt-1.5 flex gap-1.5">
                <button
                  type="button"
                  className="rounded-[3px] border border-line-strong px-2 py-0.5 text-[11.5px] hover:bg-surface-2"
                  onClick={() => {
                    setRows(null);
                    app.navigate("analysis", { symbol: row.symbol });
                  }}
                >
                  Analyse {row.symbol}
                </button>
                <button
                  type="button"
                  className="rounded-[3px] border border-line-strong px-2 py-0.5 text-[11.5px] hover:bg-surface-2"
                  onClick={() => {
                    setRows(null);
                    app.navigate("watchlists", { symbol: row.symbol });
                  }}
                >
                  Add to watchlist
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </form>
  );
}
