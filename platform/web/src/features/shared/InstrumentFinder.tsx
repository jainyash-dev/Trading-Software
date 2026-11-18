import { useState } from "react";
import { Button, TextInput } from "../../design/components";
import { useAppState } from "../../state/store";
import type { Instrument } from "../../types/contracts";

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

export function InstrumentFinder(props: {
  onSelect: (instrument: Instrument) => void;
  label?: string;
  inputId?: string;
}) {
  const app = useAppState();
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<Instrument[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function search() {
    const text = query.trim();
    if (!text) {
      setRows(null);
      setError("Enter a symbol, name, or ISIN.");
      return;
    }
    setLoading(true);
    setError(null);
    const result = await app.request<{ instruments?: unknown[] }>("/api/v1/instruments", { query: { query: text } });
    setLoading(false);
    if (!result.ok) {
      app.reportFailure(result);
      setRows(null);
      setError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    const instruments = (result.envelope.data.instruments ?? []).map(asInstrument).filter((item): item is Instrument => item !== null);
    setRows(instruments);
  }

  return (
    <div className="space-y-2">
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void search();
        }}
      >
        <TextInput
          id={props.inputId}
          label={props.label ?? "Instrument"}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Symbol, name, or ISIN"
        />
        <Button type="submit" disabled={loading || app.connection !== "connected"}>
          {loading ? "Searching" : "Search instruments"}
        </Button>
      </form>
      {error ? <p className="text-[12px] text-muted">{error}</p> : null}
      {rows && rows.length === 0 ? (
        <p className="border border-dashed border-line px-3 py-3 text-[12px]">No instrument matched. The text was not added.</p>
      ) : null}
      {rows && rows.length > 0 ? (
        <ul className="border border-line" aria-label="Instrument results">
          {rows.map((row) => (
            <li key={`${row.symbol}-${row.isin ?? ""}`} className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-2 py-2 last:border-b-0">
              <span className="text-[12px]">
                <span className="font-semibold">{row.symbol}</span>
                <span className="text-muted"> {row.name ?? "Name unavailable"}</span>
                <span className="text-muted"> · ISIN {row.isin ?? "unavailable"}</span>
                <span className="text-muted"> · verified {row.verified ? "true" : "false"}</span>
              </span>
              <Button type="button" onClick={() => props.onSelect(row)}>
                Use {row.symbol}
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
