import { useEffect, useState } from "react";
import { Button, DataTable, EmptyState, Page, Panel, ProvenanceBadge, Skeleton, Switch } from "../../design/components";
import { useAppState } from "../../state/store";
import type { ApiErrorBody, ScanListData, ScanSummary } from "../../types/contracts";
import { Completeness, ErrorLine } from "../shared/ui";

/** P10-5 Scan History: stored scan records with their actual completeness. Cursor paging from the API. */
export function ScanHistoryPage() {
  const app = useAppState();
  const live = app.connection === "connected";
  const [fixtures, setFixtures] = useState(false);
  const [rows, setRows] = useState<ScanSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiErrorBody | null>(null);
  const [reload, setReload] = useState(0);

  async function load(next: string | null) {
    setLoading(true);
    const result = await app.request<ScanListData>("/api/v1/scans", {
      query: { limit: 25, ...(next ? { cursor: next } : {}), ...(fixtures ? { include_fixtures: true } : {}) },
    });
    setLoading(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setError(null);
    setRows((current) => (next ? [...current, ...(result.envelope.data.scans ?? [])] : result.envelope.data.scans ?? []));
    setCursor(result.envelope.data.next_cursor ?? null);
  }

  useEffect(() => {
    if (!live) {
      setRows([]);
      return;
    }
    void load(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, fixtures, reload]);

  const counts = rows.reduce<Record<string, number>>((acc, row) => {
    const key = row.completeness ?? "UNKNOWN";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Page
      eyebrow="Research"
      title="Scan History"
      description="Every stored scan result, newest first. Completeness is what the pipeline recorded. A partial or failed scan is never shown as complete."
      actions={
        <>
          <Switch label="Include fixture scans" checked={fixtures} onChange={setFixtures} />
          <Button type="button" onClick={() => setReload((value) => value + 1)} disabled={!live}>
            Refresh
          </Button>
          <Button type="button" variant="primary" onClick={() => app.navigate("scanner")}>
            New scan
          </Button>
        </>
      }
    >
      {!live ? <EmptyState title="Scan history unavailable" reason="The API session is not connected." /> : null}
      {error ? <ErrorLine error={error} onRetry={() => setReload((value) => value + 1)} /> : null}
      {live ? (
        <Panel
          title={`${rows.length} stored scan${rows.length === 1 ? "" : "s"} loaded`}
          subtitle={Object.keys(counts).length ? Object.entries(counts).map(([key, value]) => `${key} ${value}`).join(" · ") : "Counts are of the rows loaded on this page."}
          flush
        >
          {loading && rows.length === 0 ? (
            <div className="p-3.5">
              <Skeleton rows={4} />
            </div>
          ) : null}
          {!loading && rows.length === 0 && !error ? (
            <div className="p-3.5">
              <EmptyState title="No stored scans" reason={fixtures ? "No scan, including fixtures, is stored." : "No non-fixture scan is stored. Fixture runs are hidden."} />
            </div>
          ) : null}
          {rows.length ? (
            <div className="p-3.5">
              <DataTable<ScanSummary & { id: string }>
                caption="Scan history"
                rows={rows.map((row) => ({ ...row, id: row.scan_key }))}
                onActivate={(row) => app.navigate("scanner", { scan: row.scan_key, fixtures: row.fixture ? "1" : null })}
                columns={[
                  { key: "scan", header: "Scan", sortValue: (row) => row.scan_key, render: (row) => <span className="code">{row.scan_key}</span> },
                  { key: "as_of", header: "As of", sortValue: (row) => row.as_of ?? "", render: (row) => <span className="tabular">{row.as_of ?? "Unavailable"}</span> },
                  { key: "type", header: "Trade type", sortValue: (row) => row.trade_type ?? "", render: (row) => row.trade_type ?? "Unavailable" },
                  { key: "universe", header: "Universe", render: (row) => row.universe ?? "Unavailable" },
                  { key: "full", header: "Full universe", render: (row) => String(row.full_universe_scan === true) },
                  { key: "completeness", header: "Completeness", sortValue: (row) => row.completeness ?? "", render: (row) => <Completeness value={row.completeness} /> },
                  {
                    key: "limits",
                    header: "Limitations",
                    numeric: true,
                    render: (row) => (Array.isArray(row.limitations) ? <span title={row.limitations.join(", ")}>{row.limitations.length}</span> : "—"),
                  },
                  { key: "source", header: "Data", render: (row) => (row.fixture ? <ProvenanceBadge kind="FIXTURE" /> : <ProvenanceBadge kind="EXPLORATORY" />) },
                  {
                    key: "open",
                    header: "",
                    render: (row) => (
                      <Button size="sm" type="button" onClick={() => app.navigate("scanner", { scan: row.scan_key, fixtures: row.fixture ? "1" : null })}>
                        Inspect
                      </Button>
                    ),
                  },
                ]}
              />
              {cursor ? (
                <div className="mt-3 flex justify-center">
                  <Button type="button" disabled={loading} onClick={() => void load(cursor)}>
                    {loading ? "Loading…" : "Load older scans"}
                  </Button>
                </div>
              ) : (
                <p className="mt-3 text-center text-[11.5px] text-muted">End of stored history.</p>
              )}
            </div>
          ) : null}
        </Panel>
      ) : null}
    </Page>
  );
}
