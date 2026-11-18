import { useEffect, useState } from "react";
import { Button, Dialog, EmptyState, Skeleton, TextInput, Unavailable } from "../../design/components";
import { connectionLabel } from "../../services/connection";
import { newIdempotencyKey } from "../../services/idempotency";
import { useAppState } from "../../state/store";
import type { ApiErrorBody, Instrument, Watchlist } from "../../types/contracts";
import { InstrumentFinder } from "../shared/InstrumentFinder";
import { ErrorLine, Fact, FactGrid, Section } from "../shared/ui";
import { clearPendingWatchlist, readPendingWatchlist, writePendingWatchlist } from "./storage";

export function WatchlistsPage() {
  const app = useAppState();
  const request = app.request;
  const reportFailure = app.reportFailure;
  const query = new URLSearchParams(app.queryString);
  const [lists, setLists] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiErrorBody | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(query.get("watchlist"));
  const [name, setName] = useState("");
  const [rename, setRename] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<string | null>(null);
  const [pendingDeleteList, setPendingDeleteList] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resume, setResume] = useState(readPendingWatchlist());
  const [names, setNames] = useState<Record<string, Instrument>>({});
  const [reloadKey, setReloadKey] = useState(0);
  const connected = app.connection === "connected";
  const selected = lists.find((list) => list.watchlist_id === selectedId) ?? null;

  useEffect(() => {
    const wanted = new URLSearchParams(app.queryString).get("watchlist");
    if (wanted) setSelectedId(wanted);
  }, [app.queryString]);

  useEffect(() => {
    if (!connected) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    void request<{ watchlists?: Watchlist[] }>("/api/v1/watchlists", { signal: controller.signal }).then((result) => {
      if (!active) return;
      setLoading(false);
      if (!result.ok) {
        reportFailure(result);
        setError(result.error);
        return;
      }
      const rows = result.envelope.data.watchlists ?? [];
      setLists(rows);
      setError(null);
      setSelectedId((current) => current && rows.some((row) => row.watchlist_id === current) ? current : rows[0]?.watchlist_id ?? null);
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [connected, app.revision, reloadKey, request, reportFailure]);

  useEffect(() => {
    if (!selected) return;
    setRename(selected.name);
    const controller = new AbortController();
    let active = true;
    for (const symbol of selected.symbols) {
      void request<{ instruments?: unknown[] }>("/api/v1/instruments", { query: { query: symbol }, signal: controller.signal }).then((result) => {
        if (!active || !result.ok) return;
        const match = (result.envelope.data.instruments ?? [])
          .map(asInstrument)
          .find((item) => item?.symbol === symbol);
        if (!match) return;
        setNames((current) => ({ ...current, [symbol]: match }));
      });
    }
    return () => {
      active = false;
      controller.abort();
    };
  }, [selected, request]);

  async function create(pendingName: string, symbols: string[], key: string) {
    const trimmed = pendingName.trim();
    if (!trimmed || trimmed.length > 80) {
      setFormError("name is required");
      return;
    }
    setSaving(true);
    setFormError(null);
    writePendingWatchlist({ idempotencyKey: key, name: trimmed, symbols });
    const result = await request<Watchlist>("/api/v1/watchlists", {
      method: "POST",
      idempotencyKey: key,
      body: { name: trimmed, symbols },
    });
    setSaving(false);
    if (!result.ok) {
      reportFailure(result);
      setFormError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    clearPendingWatchlist();
    setResume(null);
    setName("");
    setLists((current) => {
      const without = current.filter((item) => item.watchlist_id !== result.envelope.data.watchlist_id);
      return [...without, result.envelope.data];
    });
    setSelectedId(result.envelope.data.watchlist_id);
  }

  async function patch(watchlistId: string, body: { name?: string; symbols?: string[] }) {
    setSaving(true);
    setFormError(null);
    const result = await request<Watchlist>(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}`, { method: "PATCH", body });
    setSaving(false);
    if (!result.ok) {
      reportFailure(result);
      setFormError(`${result.error.code}: ${result.error.message}`);
      setReloadKey((value) => value + 1);
      return;
    }
    setLists((current) => current.map((item) => (item.watchlist_id === watchlistId ? result.envelope.data : item)));
  }

  async function removeList(watchlistId: string) {
    setSaving(true);
    setFormError(null);
    const result = await request<{ deleted?: boolean }>(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}`, {
      method: "DELETE",
    });
    setSaving(false);
    if (!result.ok) {
      reportFailure(result);
      setFormError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    setLists((current) => current.filter((item) => item.watchlist_id !== watchlistId));
    setSelectedId((current) => (current === watchlistId ? null : current));
    app.navigate("watchlists", {});
  }

  const hinted = query.get("symbol");

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-4 px-5 py-4">
      <header className="border-b border-line pb-3">
        <p className="eyebrow">Overview</p>
          <h1 className="mt-0.5 text-[19px] font-semibold leading-6 tracking-[-0.01em]">Watchlists</h1>
        <p className="mt-1 max-w-4xl text-[12.5px] leading-[1.5] text-muted">
          Private lists for organising symbols. A watchlist is not the Nifty 100, not a scan, and not a qualified opportunity. Prices are not supplied.
        </p>
      </header>
      {!connected ? (
        <EmptyState
          title={connectionLabel(app.connection)}
          reason="Saved watchlists stay on the platform. This page did not create one."
        />
      ) : null}
      {error ? <ErrorLine error={error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
      {loading && connected ? <Skeleton rows={3} /> : null}

      <div className="grid items-start gap-3 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Section title="Lists">
          {connected && !loading && lists.length === 0 ? (
            <EmptyState title="No watchlist is stored" reason="Create one with a name. Symbols are optional." />
          ) : null}
          <ul className="space-y-1">
            {lists.map((list) => (
              <li key={list.watchlist_id}>
                <button
                  type="button"
                  className={`w-full border px-2 py-2 text-left text-[12px] ${list.watchlist_id === selected?.watchlist_id ? "border-line bg-[var(--gtf-neutral-bg)]" : "border-transparent"}`}
                  onClick={() => {
                    setSelectedId(list.watchlist_id);
                    app.navigate("watchlists", { watchlist: list.watchlist_id, ...(hinted ? { symbol: hinted } : {}) });
                  }}
                >
                  <span className="font-semibold">{list.name}</span>
                  <span className="block text-muted">{Array.isArray(list.symbols) ? `${list.symbols.length} symbols` : "symbol count unavailable"}</span>
                </button>
              </li>
            ))}
          </ul>
          <form
            className="space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              void create(name, [], newIdempotencyKey());
            }}
          >
            <TextInput label="New watchlist" value={name} onChange={(event) => setName(event.target.value)} />
            <Button type="submit" variant="primary" disabled={!connected || saving}>
              Create watchlist
            </Button>
          </form>
          {resume ? (
            <p className="text-[12px]">
              A create for {resume.name} was not confirmed. Resume uses the same idempotency key.
              <Button type="button" className="ml-2" onClick={() => void create(resume.name, resume.symbols, resume.idempotencyKey)}>
                Resume create
              </Button>
            </p>
          ) : null}
          {formError ? <p className="text-[12px]">{formError}</p> : null}
        </Section>

        <Section title={selected ? selected.name : "Watchlist"}>
          {!selected && !loading ? <EmptyState title="No watchlist is selected" reason="Create or choose a list. Nothing was added automatically." /> : null}
          {selected ? (
            <div className="space-y-3">
              <FactGrid>
                <Fact label="Symbols">{selected.symbols.length}</Fact>
                <Fact label="Updated">{selected.updated_at || selected.created_at || <Unavailable />}</Fact>
                <Fact label="Eligibility">{selected.eligibility == null ? <Unavailable /> : String(selected.eligibility)}</Fact>
              </FactGrid>
              {selected.note ? <p className="text-[12px]">{selected.note}</p> : null}
              <p className="text-[12px] text-muted">This list is not a live market view.</p>
              <form
                className="flex flex-wrap items-end gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  const trimmed = rename.trim();
                  if (!trimmed || trimmed.length > 80) {
                    setFormError("name is required");
                    return;
                  }
                  void patch(selected.watchlist_id, { name: trimmed });
                }}
              >
                <TextInput label="Rename" value={rename} onChange={(event) => setRename(event.target.value)} />
                <Button type="submit" disabled={saving}>
                  Rename
                </Button>
                <Button type="button" disabled={saving} onClick={() => setPendingDeleteList(true)}>
                  Delete list
                </Button>
              </form>
              {hinted ? <HintedSymbol symbol={hinted} request={request} onAdd={(instrument) => void patch(selected.watchlist_id, { symbols: append(selected.symbols, instrument.symbol) })} /> : null}
              <InstrumentFinder
                label="Add symbol"
                onSelect={(instrument) => void patch(selected.watchlist_id, { symbols: append(selected.symbols, instrument.symbol) })}
              />
              {selected.symbols.length === 0 ? <EmptyState title="No symbols" reason="Search returns instruments from the API. Typed text is not added by itself." /> : null}
              {selected.symbols.length > 0 ? (
                <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
                  <table className="gtf-table w-full border-collapse text-left text-[12px]">
                    <thead>
                      <tr>
                        {["Position", "Symbol", "Name", "ISIN", "Verified", ""].map((header) => (
                          <th key={header || "actions"} className="border-b border-line px-2 py-2 font-medium">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {selected.symbols.map((symbol, index) => {
                        const instrument = names[symbol];
                        return (
                          <tr key={`${symbol}-${index}`}>
                            <td className="border-b border-line px-2 py-2 tabular">{index + 1}</td>
                            <td className="border-b border-line px-2 py-2 font-medium">{symbol}</td>
                            <td className="border-b border-line px-2 py-2">{instrument?.name ?? <Unavailable />}</td>
                            <td className="border-b border-line px-2 py-2">{instrument?.isin ?? <Unavailable />}</td>
                            <td className="border-b border-line px-2 py-2">{instrument ? (instrument.verified ? "true" : "false") : <Unavailable />}</td>
                            <td className="border-b border-line px-2 py-2">
                              <div className="flex flex-wrap gap-1">
                                <Button type="button" disabled={index === 0 || saving} onClick={() => void patch(selected.watchlist_id, { symbols: move(selected.symbols, index, -1) })}>
                                  Move up
                                </Button>
                                <Button
                                  type="button"
                                  disabled={index === selected.symbols.length - 1 || saving}
                                  onClick={() => void patch(selected.watchlist_id, { symbols: move(selected.symbols, index, 1) })}
                                >
                                  Move down
                                </Button>
                                <Button type="button" onClick={() => app.navigate("scanner", { symbol })}>
                                  Evidence
                                </Button>
                                <Button type="button" onClick={() => setPendingRemove(symbol)}>
                                  Remove
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          ) : null}
        </Section>
      </div>
      {pendingRemove && selected ? (
        <Dialog
          title={`Remove ${pendingRemove}`}
          body="This replaces the stored symbol order without that symbol. It does not change a research result."
          confirm="Remove"
          onClose={() => setPendingRemove(null)}
          onConfirm={() => {
            const symbol = pendingRemove;
            setPendingRemove(null);
            void patch(selected.watchlist_id, { symbols: selected.symbols.filter((item) => item !== symbol) });
          }}
        />
      ) : null}
      {pendingDeleteList && selected ? (
        <Dialog
          title={`Delete ${selected.name}`}
          body="This deletes the watchlist and its symbols. It does not change scanner eligibility or opportunity workflow records."
          confirm="Delete watchlist"
          onClose={() => setPendingDeleteList(false)}
          onConfirm={() => {
            const id = selected.watchlist_id;
            setPendingDeleteList(false);
            void removeList(id);
          }}
        />
      ) : null}
    </section>
  );
}

function HintedSymbol(props: {
  symbol: string;
  request: ReturnType<typeof useAppState>["request"];
  onAdd: (instrument: Instrument) => void;
}) {
  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [empty, setEmpty] = useState(false);
  const symbol = props.symbol;
  const request = props.request;
  useEffect(() => {
    const controller = new AbortController();
    void request<{ instruments?: unknown[] }>("/api/v1/instruments", { query: { query: symbol }, signal: controller.signal }).then((result) => {
      if (!result.ok) return;
      const match = (result.envelope.data.instruments ?? []).map(asInstrument).find((item) => item?.symbol === symbol) ?? null;
      setInstrument(match);
      setEmpty(!match);
    });
    return () => controller.abort();
  }, [request, symbol]);
  if (empty) return <p className="text-[12px]">No instrument was returned for {props.symbol}. It was not added.</p>;
  if (!instrument) return <p className="text-[12px]">Checking {props.symbol} against the instruments endpoint.</p>;
  return (
    <p className="text-[12px]">
      {instrument.symbol} · {instrument.name ?? "Name unavailable"} · ISIN {instrument.isin ?? "unavailable"} · verified {instrument.verified ? "true" : "false"}
      <Button type="button" className="ml-2" onClick={() => props.onAdd(instrument)}>
        Add {instrument.symbol}
      </Button>
    </p>
  );
}

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

function append(symbols: string[], symbol: string): string[] {
  return symbols.includes(symbol) ? symbols : [...symbols, symbol];
}

function move(symbols: string[], index: number, direction: -1 | 1): string[] {
  const target = index + direction;
  if (target < 0 || target >= symbols.length) return symbols;
  const next = [...symbols];
  const [item] = next.splice(index, 1);
  next.splice(target, 0, item);
  return next;
}
