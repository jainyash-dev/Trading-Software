import { useState } from "react";
import { Button, Callout, EmptyState, KeyValue, Page, Panel, ProvenanceBadge, SelectInput, Switch, TextInput } from "../../design/components";
import { useAppState } from "../../state/store";
import type { ScanListData } from "../../types/contracts";
import { Warning } from "../shared/ui";
import { dataOf, useApi } from "../shared/useApi";

/**
 * P10-9 Backtesting. Posts to the existing /api/v1/backtests route. Every assumption is an owner
 * input. The result is labelled NOT_PERFORMANCE_EVIDENCE; no win rate, expectancy or drawdown is shown.
 */
export function BacktestPage() {
  const app = useAppState();
  const [symbols, setSymbols] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [cost, setCost] = useState("");
  const [slip, setSlip] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const connected = app.connection === "connected";
  return (
    <Page
      eyebrow="Intelligence"
      title="Backtesting"
      description="A result is arithmetic on research signals. It is not evidence that the methodology works. Release gate R4 stays open."
      meta={<ProvenanceBadge kind="PARTIAL" title="Run route exists; no run list, manifest store or analytics" />}
    >
      <div className="grid items-start gap-4 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Panel title="Study inputs" subtitle="All costs and slippage are owner-supplied. No brokerage tariff is built in (B12).">
          <form
            className="space-y-2.5"
            onSubmit={(event) => {
              event.preventDefault();
              setRunning(true);
              void app
                .request<Record<string, unknown>>("/api/v1/backtests", {
                  method: "POST",
                  body: {
                    symbols: symbols.split(",").map((item) => item.trim()).filter(Boolean),
                    start,
                    end,
                    // P10 review I-2: blank stays null so the backend refuses it; it never becomes 0.
                    cost_pct_per_side: cost.trim() === "" ? null : Number(cost),
                    slippage_pct_per_side: slip.trim() === "" ? null : Number(slip),
                  },
                })
                .then((response) => {
                  setRunning(false);
                  if (!response.ok) setMessage(`${response.error.code}: ${response.error.message}`);
                  else {
                    setResult(response.envelope.data);
                    setMessage(null);
                  }
                });
            }}
          >
            <TextInput label="Symbols" placeholder="Comma separated, e.g. RELIANCE, TCS" value={symbols} onChange={(event) => setSymbols(event.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <TextInput label="Start" placeholder="YYYY-MM-DD" value={start} onChange={(event) => setStart(event.target.value)} />
              <TextInput label="End" placeholder="YYYY-MM-DD" value={end} onChange={(event) => setEnd(event.target.value)} />
              <TextInput label="Cost percent per side" inputMode="decimal" value={cost} onChange={(event) => setCost(event.target.value)} />
              <TextInput label="Slippage percent per side" inputMode="decimal" value={slip} onChange={(event) => setSlip(event.target.value)} />
            </div>
            <Button type="submit" variant="primary" disabled={!connected || running}>
              {running ? "Running…" : "Run labelled study"}
            </Button>
            {!connected ? <p className="text-[11.5px] text-muted">Needs the API session.</p> : null}
          </form>
        </Panel>
        <div className="space-y-4">
          {message ? <Warning>{message}</Warning> : null}
          {result ? (
            <Panel title="Study result" subtitle="Not stored as a run. Re-run to reproduce.">
              <Warning>
                NOT_PERFORMANCE_EVIDENCE. R4 is {String(result.release_gate_r4)}. Sample size {String(result.sample_size ?? "unavailable")}. {String(result.cost_note || "")}
              </Warning>
              <KeyValue
                rows={[
                  ["Closed trades", String((result.metrics as { closed?: unknown } | undefined)?.closed ?? "unavailable")],
                  ["Sample size", String(result.sample_size ?? "unavailable")],
                  ["Release gate R4", String(result.release_gate_r4 ?? "unavailable")],
                  ["Limitations", Array.isArray(result.limitations) ? result.limitations.join(", ") : "unavailable"],
                ]}
              />
              <p className="text-[11.5px] text-muted">This is not a win-rate claim. Win rate, expectancy and drawdown are not displayed.</p>
            </Panel>
          ) : (
            <Panel title="Study result">
              <EmptyState
                title="No study run in this session"
                reason="Win rate, expectancy, and drawdown stay hidden until this run returns a manifest-labelled result. The journal win rate is not shown here."
              />
            </Panel>
          )}
          <Callout tone="neutral" title="What this screen does not do yet">
            There is no run history, manifest viewer, equity curve or walk-forward screen: the platform API has no route for them. Walk-forward and sensitivity runs exist in the research CLI
            (<span className="code">backtest-walk-forward</span>, <span className="code">backtest-sensitivity</span>) and need certified history (P0) and the owner execution model (B9, B12) before any result can be quoted.
          </Callout>
        </div>
      </div>
    </Page>
  );
}

const REPORT_FILES = ["candidates.csv", "fresh_zones.csv", "blocked_zones.csv", "data_quality.csv", "summary.json", "scan.json", "readiness.json", "run_manifest.json"] as const;

/** P10-9 Research Reports. Reads report files written by the research reporter for a stored scan. */
export function ReportsPage() {
  const app = useAppState();
  const [fixtures, setFixtures] = useState(false);
  const [scanKey, setScanKey] = useState("");
  const [file, setFile] = useState<(typeof REPORT_FILES)[number]>("candidates.csv");
  const [body, setBody] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const scans = useApi<ScanListData>("/api/v1/scans", { limit: 50, ...(fixtures ? { include_fixtures: true } : {}) });
  const rows = dataOf(scans)?.scans ?? [];
  const selected = rows.find((row) => row.scan_key === scanKey);
  return (
    <Page
      eyebrow="Intelligence"
      title="Research Reports"
      description="Export reads the report file written by the research reporter for that scan. The bytes are shown as stored; nothing is regenerated."
    >
      <div className="grid items-start gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Panel title="Report">
          <Switch label="Include fixture scans" checked={fixtures} onChange={(value) => { setFixtures(value); setScanKey(""); }} />
          <SelectInput label="Scan key" value={scanKey} onChange={(event) => { setScanKey(event.target.value); setBody(null); }}>
            <option value="">Choose a stored scan</option>
            {rows.map((row) => (
              <option key={row.scan_key} value={row.scan_key}>
                {row.scan_key} · {row.as_of?.slice(0, 10) ?? "?"} · {row.completeness ?? "?"}
                {row.fixture ? " · FIXTURE" : ""}
              </option>
            ))}
          </SelectInput>
          <SelectInput label="File" value={file} onChange={(event) => { setFile(event.target.value as (typeof REPORT_FILES)[number]); setBody(null); }}>
            {REPORT_FILES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </SelectInput>
          <Button
            type="button"
            variant="primary"
            disabled={!scanKey}
            onClick={() =>
              void app.request<{ body?: string }>(`/api/v1/scans/${encodeURIComponent(scanKey)}/reports/${file}`).then((result) => {
                if (!result.ok) {
                  setMessage(`${result.error.code}: ${result.error.message}`);
                  setBody(null);
                } else {
                  setBody(result.envelope.data.body || "");
                  setMessage(null);
                }
              })
            }
          >
            Export {file}
          </Button>
        </Panel>
        <Panel
          title={body != null ? `${file} · ${scanKey}` : "Preview"}
          actions={
            body != null && selected && !selected.fixture ? (
              <Button
                type="button"
                size="sm"
                onClick={() => {
                  const blob = new Blob([body], { type: file.endsWith(".csv") ? "text/csv" : "application/json" });
                  const link = document.createElement("a");
                  link.href = URL.createObjectURL(blob);
                  link.download = `${scanKey}-${file}`;
                  link.click();
                  URL.revokeObjectURL(link.href);
                }}
              >
                Save file
              </Button>
            ) : null
          }
        >
          {message ? <Warning>{message}</Warning> : null}
          {selected?.fixture ? <Warning>FIXTURE_NOT_MARKET_DATA. Saving a fixture report is disabled because the stored file body does not carry the fixture label (specification 5.13).</Warning> : null}
          {body == null && !message ? <EmptyState title="Nothing exported" reason="Choose a stored scan and a report file." /> : null}
          {body != null ? <pre className="scroll-thin code max-h-[32rem] overflow-auto whitespace-pre rounded-[4px] border border-line bg-surface-2 p-3">{body}</pre> : null}
        </Panel>
      </div>
    </Page>
  );
}
