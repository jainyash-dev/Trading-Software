import { useEffect, useState } from "react";
import { Button, EmptyState, KeyValue, Page, Panel, ProvenanceBadge, SelectInput, Skeleton, Switch } from "../../design/components";
import { useAppState } from "../../state/store";
import type { ApiErrorBody, ScanListData, ScanSymbolsData } from "../../types/contracts";
import { ErrorLine } from "../shared/ui";
import { dataOf, useApi } from "../shared/useApi";

interface ExplainAnswer {
  question?: string;
  result?: string;
  answer_lines?: string[];
  citations?: { gates?: string[]; rule_refs?: string[]; zone_ids?: string[]; finding_codes?: string[] };
  limitations?: string[];
  changes_status?: boolean;
  model?: string | null;
}

/**
 * P10-9 AI Research Assistant. The connected capability is the deterministic explainer
 * (GET /api/v1/symbols/{symbol}/explain): rule-based text read from a stored scan, with
 * citations. No language model is connected (AI-002 owner-deferred). Nothing here writes
 * a gate, a status or an order, and nothing is a buy or sell signal.
 */
export function AssistantPage() {
  const app = useAppState();
  const live = app.connection === "connected";
  const [fixtures, setFixtures] = useState(false);
  const [scan, setScan] = useState("");
  const [symbol, setSymbol] = useState("");
  const [answer, setAnswer] = useState<ExplainAnswer | null>(null);
  const [error, setError] = useState<ApiErrorBody | null>(null);
  const [asking, setAsking] = useState(false);
  const scans = useApi<ScanListData>("/api/v1/scans", { limit: 25, ...(fixtures ? { include_fixtures: true } : {}) });
  const symbols = useApi<ScanSymbolsData>(scan ? `/api/v1/scans/${encodeURIComponent(scan)}/symbols` : null, fixtures ? { include_fixtures: true } : undefined);
  const scanRows = dataOf(scans)?.scans ?? [];
  const symbolRows = (dataOf(symbols)?.symbols ?? []).map((row) => row.symbol).filter((value): value is string => Boolean(value));

  useEffect(() => {
    setSymbol("");
    setAnswer(null);
    setError(null);
  }, [scan]);
  useEffect(() => {
    setAnswer(null);
    setError(null);
  }, [symbol]);

  async function ask() {
    if (!scan || !symbol) return;
    setAsking(true);
    const result = await app.request<ExplainAnswer>(`/api/v1/symbols/${encodeURIComponent(symbol)}/explain`, {
      query: { scan_key: scan, ...(fixtures ? { include_fixtures: true } : {}) },
    });
    setAsking(false);
    if (result.ok) {
      setAnswer(result.envelope.data);
      setError(null);
    } else {
      setAnswer(null);
      setError(result.error);
    }
  }

  const selected = scanRows.find((row) => row.scan_key === scan);

  return (
    <Page
      eyebrow="Intelligence"
      title="AI Research Assistant"
      description="Explains a stored scan decision in words, with citations to gates, rule references and zones. The explanation is deterministic. It cannot change a status and it is not a trade signal."
      meta={
        <>
          {live ? <ProvenanceBadge kind="LIVE" title="Deterministic explain route" /> : <ProvenanceBadge kind="UNAVAILABLE" title="API not connected" />}
          <span className="text-[11.5px] text-muted">{live ? "Deterministic explainer connected" : "Deterministic explainer unavailable (API not connected)"}</span>
          <ProvenanceBadge kind="NOT_IMPLEMENTED" title="AI-002: no owner-approved language-model provider" />
          <span className="text-[11.5px] text-muted">Language model not connected</span>
        </>
      }
    >
      {!live ? <EmptyState title="Assistant off" reason="The API session is not connected. Nothing is sent off this machine." /> : null}
      {live ? (
        <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
          <Panel title="Ask about a stored decision" subtitle="Scope: one stored scan and one symbol.">
            <Switch label="Include fixture scans" checked={fixtures} onChange={(value) => { setFixtures(value); setScan(""); }} />
            {scans.state === "loading" ? <Skeleton rows={1} /> : null}
            {scans.state === "error" ? <ErrorLine error={scans.error} /> : null}
            <SelectInput label="Stored scan" value={scan} onChange={(event) => setScan(event.target.value)}>
              <option value="">Choose a scan</option>
              {scanRows.map((row) => (
                <option key={row.scan_key} value={row.scan_key}>
                  {row.scan_key} · {row.as_of?.slice(0, 10) ?? "?"} · {row.completeness ?? "?"}
                  {row.fixture ? " · FIXTURE" : ""}
                </option>
              ))}
            </SelectInput>
            <SelectInput label="Symbol in that scan" value={symbol} disabled={!scan} onChange={(event) => setSymbol(event.target.value)}>
              <option value="">{scan ? (symbols.state === "loading" ? "Loading symbols…" : "Choose a symbol") : "Choose a scan first"}</option>
              {symbolRows.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </SelectInput>
            <Button type="button" variant="primary" disabled={!scan || !symbol || asking} onClick={() => void ask()}>
              {asking ? "Explaining…" : "Why this status?"}
            </Button>
            {scans.state === "ready" && scanRows.length === 0 ? <p className="text-[12px] text-muted">No stored scan. Run a scan first.</p> : null}
            <p className="text-[11.5px] text-muted">
              A free-text question box is not offered: there is no language model, and the explainer answers only “why does this symbol have this status in this scan”.
            </p>
          </Panel>
          <Panel
            title={answer ? `${symbol} in ${scan}` : "Answer"}
            subtitle={selected ? `As of ${selected.as_of ?? "unavailable"} · ${selected.fixture ? "FIXTURE_NOT_MARKET_DATA" : "not P0 certified"}` : undefined}
            actions={
              answer && symbol ? (
                <Button type="button" size="sm" onClick={() => app.navigate("analysis", { symbol, scan, fixtures: fixtures ? "1" : null })}>
                  Open in Stock Analysis
                </Button>
              ) : null
            }
          >
            {error ? <ErrorLine error={error} onRetry={() => void ask()} /> : null}
            {!answer && !error ? <EmptyState title="No question asked" reason="Choose a stored scan and a symbol. The answer is read from the stored scan; nothing is recomputed." /> : null}
            {answer ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="eyebrow">Result</span>
                  <span className="code">{answer.result ?? "UNAVAILABLE"}</span>
                  {selected?.fixture ? <ProvenanceBadge kind="FIXTURE" /> : null}
                </div>
                <ol className="space-y-1.5 border-l-2 border-line pl-3 text-[12.5px] leading-[1.55]" data-testid="assistant-answer">
                  {(answer.answer_lines ?? []).map((line, index) => (
                    <li key={`${index}-${line.slice(0, 24)}`}>{line}</li>
                  ))}
                </ol>
                <KeyValue
                  rows={[
                    ["Gates cited", answer.citations?.gates?.join(", ") || "None"],
                    ["Rule references", answer.citations?.rule_refs?.join(", ") || "None"],
                    ["Zones cited", answer.citations?.zone_ids?.join(", ") || "None"],
                    ["Finding codes", answer.citations?.finding_codes?.join(", ") || "None"],
                    ["Changes status", answer.changes_status === undefined ? "not returned" : String(answer.changes_status)],
                    ["Model", answer.model ?? "none (deterministic)"],
                  ]}
                />
                {answer.limitations?.length ? (
                  <ul className="space-y-1 text-[11.5px] text-muted">
                    {answer.limitations.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : null}
          </Panel>
        </div>
      ) : null}
    </Page>
  );
}
