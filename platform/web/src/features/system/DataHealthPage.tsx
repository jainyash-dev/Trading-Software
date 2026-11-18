import { useState } from "react";
import { Button, DataTable, EmptyState, KeyValue, Metric, Page, Panel, ProvenanceBadge, Skeleton, Unavailable } from "../../design/components";
import { presentLimitation } from "../../design/status";
import { isoDate } from "../../services/idempotency";
import { useAppState } from "../../state/store";
import type { CalendarData, DatasetRow, DatasetsData, OverviewData, UniverseData } from "../../types/contracts";
import { ErrorLine } from "../shared/ui";
import { dataOf, useApi } from "../shared/useApi";

/** P10-10 Data Health. Reads health, datasets, universe, calendar and overview. Never upgrades a state. */
export function DataHealthPage() {
  const app = useAppState();
  const [reload, setReload] = useState(0);
  const live = app.connection === "connected";
  const health = live ? app.health : null;
  const day = isoDate(health?.last_successful_ingest_date) ?? isoDate(health?.last_scan?.as_of);
  const datasets = useApi<DatasetsData>("/api/v1/datasets", undefined, reload);
  const universe = useApi<UniverseData>(day ? "/api/v1/universe" : null, { as_of: day ?? undefined }, reload);
  const calendar = useApi<CalendarData>(day ? "/api/v1/calendar" : null, { date: day ?? undefined }, reload);
  const overview = useApi<OverviewData>("/api/v1/overview", day ? { as_of: day } : undefined, reload);
  const ov = dataOf(overview);
  const uni = dataOf(universe);
  const certified = health?.certified_p0_data === true;
  const limitations = [
    ...(health?.data_limitations ?? []),
    ...(dataOf(datasets)?.limitations ?? []),
    ...(uni?.limitations ?? []),
    ...(ov?.limitations ?? []),
    ...(ov?.coverage?.limitations ?? []),
  ].filter((code, index, all) => all.indexOf(code) === index);
  const rows = (dataOf(datasets)?.datasets ?? []).map((row, index) => ({ ...row, id: row.dataset_id ?? `dataset-${index}` }));

  return (
    <Page
      eyebrow="System"
      title="Data Health"
      description="What data the platform holds, how far it reaches and what is not certified. Loaded data is not certified data. Prices are not adjusted from this screen."
      actions={
        <Button type="button" onClick={() => setReload((value) => value + 1)} disabled={!live}>
          Refresh
        </Button>
      }
      meta={live ? <ProvenanceBadge kind={certified ? "CERTIFIED" : "PROVISIONAL"} title="certified_p0_data from /api/v1/health" /> : <ProvenanceBadge kind="UNAVAILABLE" />}
    >
      {!live ? <EmptyState title="Data health unavailable" reason="The API session is not connected. Nothing is shown from a previous session." /> : null}
      {live ? (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            <Metric label="Latest EOD date" value={health?.last_successful_ingest_date ?? null} sub="Last successful ingest (end of day, not live)" />
            <Metric
              label="P0 certification"
              value={certified ? "Certified" : "Not certified"}
              tone={certified ? "neutral" : "manual"}
              sub="certified_p0_data from health"
            />
            <Metric label="Data ready" value={typeof health?.data_ready === "boolean" ? (health.data_ready ? "true" : "false") : null} tone={health?.data_ready ? "neutral" : "manual"} sub={health?.data_ready_reason ?? ov?.data_ready_reason ?? "DATA_READY is not claimed."} />
            <Metric label="Readiness state" value={health?.readiness_state ?? ov?.readiness_state ?? null} sub="evaluate_data_ready on the server" />
            <Metric
              label="Universe"
              value={Array.isArray(uni?.members) ? uni.members.length : null}
              unit="members"
              sub={uni ? `${uni.name ?? "Name unavailable"} · certified ${String(uni.certified === true)}` : "Universe needs a session date"}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
            <Panel title="Datasets" subtitle="From /api/v1/datasets. A manifest hash identifies the files; it does not certify them.">
              {datasets.state === "loading" ? <Skeleton rows={2} /> : null}
              {datasets.state === "error" ? <ErrorLine error={datasets.error} onRetry={() => setReload((value) => value + 1)} /> : null}
              {datasets.state === "ready" && rows.length === 0 ? <EmptyState title="No dataset" reason="The datasets route returned no dataset id." /> : null}
              {rows.length ? (
                <DataTable<DatasetRow & { id: string }>
                  caption="Datasets"
                  rows={rows}
                  columns={[
                    { key: "id", header: "Dataset", render: (row) => <span className="code" title={row.dataset_id}>{(row.dataset_id ?? "").slice(0, 16)}…</span> },
                    { key: "files", header: "Files", numeric: true, render: (row) => (typeof row.file_count === "number" ? row.file_count : <Unavailable />) },
                    { key: "validation", header: "Research validation", render: (row) => String(row.research_validation ?? "unavailable") },
                    { key: "ready", header: "data_ready", render: (row) => String(row.data_ready ?? "unavailable") },
                    {
                      key: "kind",
                      header: "Provenance",
                      render: (row) => (row.fixture === true ? <ProvenanceBadge kind="FIXTURE" /> : <ProvenanceBadge kind="EXPLORATORY" title="Not P0 certified" />),
                    },
                  ]}
                />
              ) : null}
            </Panel>
            <Panel title="Service health" subtitle="From /api/v1/health">
              <KeyValue
                rows={[
                  ["Application status", health?.outcome ?? <Unavailable />],
                  ["Platform database", reach(health?.database_files?.platform?.reachable)],
                  ["Research database", reach(health?.database_files?.research?.reachable)],
                  ["Scheduler", health?.scheduler_state ?? <Unavailable />],
                  ["Last scan", health?.last_scan ? `${health.last_scan.scan_key} · ${health.last_scan.completeness}` : <Unavailable />],
                  ["orders_placed", typeof health?.orders_placed === "boolean" ? String(health.orders_placed) : <Unavailable />],
                ]}
              />
            </Panel>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Panel title="Limitations and validation findings" subtitle="Every code returned by health, datasets, universe and overview.">
              {limitations.length === 0 ? (
                <p className="text-[12.5px] text-muted">No limitation code was returned. This is not a certification.</p>
              ) : (
                <ul className="divide-y divide-line text-[12.5px]">
                  {limitations.map((code) => (
                    <li key={code} className="flex flex-wrap items-baseline justify-between gap-2 py-1.5">
                      <span className="code">{code}</span>
                      <span className="text-muted">{presentLimitation(code).startsWith("Unknown limitation") ? "Returned by the API" : presentLimitation(code)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
            <Panel title="Calendar, coverage and identity">
              <KeyValue
                rows={[
                  [
                    `Calendar ${day ?? ""}`.trim(),
                    calendar.state === "ready" ? (
                      [calendar.data.status, calendar.data.classification, calendar.data.reason].filter(Boolean).join(" · ") || <Unavailable />
                    ) : calendar.state === "error" ? (
                      `${calendar.error.code}: ${calendar.error.message}`
                    ) : (
                      <Unavailable />
                    ),
                  ],
                  ["Incomplete symbols", ov?.coverage?.incomplete_symbols?.length ? ov.coverage.incomplete_symbols.join(", ") : ov ? "None returned" : <Unavailable />],
                  ["Coverage note", ov?.coverage?.note ?? <Unavailable />],
                  ["Identity findings", ov?.identity_findings?.length ? ov.identity_findings.join(", ") : ov ? "None returned" : <Unavailable />],
                  ["History cut", ov?.history_cut?.applied ? `Applied for ${ov.history_cut.symbols?.join(", ") || "one or more symbols"}` : ov ? "Not applied" : <Unavailable />],
                  ["Universe certified", uni ? String(uni.certified === true) : <Unavailable />],
                ]}
              />
              <p className="text-[11.5px] text-muted">
                Missing-file and per-session coverage lists are not exposed by the platform API. Run <span className="code">python3 -m nse.research.cli eod-coverage</span> for them.
              </p>
            </Panel>
          </div>
        </>
      ) : null}
    </Page>
  );
}

function reach(value: boolean | undefined) {
  if (value === true) return "reachable";
  if (value === false) return <span className="text-[var(--gtf-fail)]">not reachable</span>;
  return <Unavailable />;
}
