import { useState } from "react";
import { Button, DataTable, EmptyState, KeyValue, Metric, Page, Panel, ProvenanceBadge, Skeleton, TextInput, Unavailable } from "../../design/components";
import { useAppState } from "../../state/store";
import type { JobData, OverviewData, OverviewJob, ScanListData, ScanSummary } from "../../types/contracts";
import { Completeness, ErrorLine, JobState } from "../shared/ui";
import { dataOf, useApi } from "../shared/useApi";

/** P10-10 Jobs and Monitoring. No job list route exists; this screen does not invent one. */
export function JobsPage() {
  const app = useAppState();
  const [reload, setReload] = useState(0);
  const [jobId, setJobId] = useState("");
  const [lookup, setLookup] = useState<{ state: "idle" | "loading" } | { state: "ready"; job: JobData } | { state: "error"; message: string }>({ state: "idle" });
  const live = app.connection === "connected";
  const health = live ? app.health : null;
  const overview = useApi<OverviewData>("/api/v1/overview", undefined, reload);
  const scans = useApi<ScanListData>("/api/v1/scans", { limit: 20, include_fixtures: true }, reload);
  const ov = dataOf(overview);
  const rows = (dataOf(scans)?.scans ?? []).map((row) => ({ ...row, id: row.scan_key }));
  const failed = rows.filter((row) => row.completeness === "FAILED").length;
  const partial = rows.filter((row) => row.completeness === "PARTIAL").length;

  async function find() {
    const id = jobId.trim();
    if (!id) {
      setLookup({ state: "error", message: "Enter a job id. The API has no job list." });
      return;
    }
    setLookup({ state: "loading" });
    const result = await app.request<JobData>(`/api/v1/jobs/${encodeURIComponent(id)}`);
    setLookup(result.ok ? { state: "ready", job: result.envelope.data } : { state: "error", message: `${result.error.code}: ${result.error.message}` });
  }

  return (
    <Page
      eyebrow="System"
      title="Jobs and Monitoring"
      description="Scheduler, the latest and active scan job, and recent scan outcomes. Readiness comes from the server; this page never shows READY on its own."
      meta={<ProvenanceBadge kind="PARTIAL" title="No job list route: only the latest and active job are returned" />}
      actions={
        <Button type="button" disabled={!live} onClick={() => setReload((value) => value + 1)}>
          Refresh
        </Button>
      }
    >
      {!live ? <EmptyState title="Monitoring unavailable" reason="The API session is not connected." /> : null}
      {live ? (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            <Metric label="Application status" value={health?.outcome ?? null} tone={health?.outcome === "FAIL" ? "fail" : health?.outcome === "OK" ? "neutral" : "manual"} sub="From /api/v1/health" />
            <Metric label="Scheduler" value={health?.scheduler_state ?? null} sub="Post-close scan when a file is already on disk" />
            <Metric label="Readiness" value={ov?.readiness_state ?? health?.readiness_state ?? null} tone="manual" sub="Server-evaluated" />
            <Metric label="Job phase" value={ov?.job_phase ?? null} sub="From /api/v1/overview" />
            <Metric label="Recent failures" value={scans.state === "ready" ? failed : null} tone={failed ? "fail" : "neutral"} sub={scans.state === "ready" ? `${partial} partial in the last ${rows.length} stored scans` : "Scan history not loaded"} />
          </div>
          {overview.state === "error" ? <ErrorLine error={overview.error} onRetry={() => setReload((value) => value + 1)} /> : null}
          <div className="grid gap-4 xl:grid-cols-3">
            <JobPanel title="Active job" job={ov?.active_job ?? null} loading={overview.state === "loading"} empty={overview.state === "ready" ? "No job is running." : "Unknown: the overview was not read."} />
            <JobPanel title="Latest job" job={ov?.job ?? null} loading={overview.state === "loading"} empty={overview.state === "ready" ? "No job record was returned." : "Unknown: the overview was not read."} />
            <Panel title="Scan due">
              {overview.state === "loading" ? <Skeleton rows={2} /> : null}
              <KeyValue
                rows={[
                  ["State", ov?.scan_due?.state ?? <Unavailable />],
                  ["As of", ov?.scan_due?.as_of ?? <Unavailable />],
                  ["Reason", ov?.scan_due?.reason ?? <Unavailable />],
                ]}
              />
            </Panel>
          </div>
          <Panel title="Recent scan outcomes" subtitle="Stored scan results, newest first, including fixture runs (labelled).">
            {scans.state === "loading" ? <Skeleton rows={3} /> : null}
            {scans.state === "error" ? <ErrorLine error={scans.error} onRetry={() => setReload((value) => value + 1)} /> : null}
            {scans.state === "ready" && rows.length === 0 ? <EmptyState title="No stored scans" reason="No scan has completed on this platform database." /> : null}
            {rows.length ? (
              <DataTable<ScanSummary & { id: string }>
                caption="Recent scan outcomes"
                rows={rows}
                onActivate={(row) => app.navigate("scanner", { scan: row.scan_key, fixtures: row.fixture ? "1" : null })}
                columns={[
                  { key: "scan", header: "Scan", sortValue: (row) => row.scan_key, render: (row) => <span className="code">{row.scan_key}</span> },
                  { key: "as_of", header: "As of", sortValue: (row) => row.as_of ?? "", render: (row) => <span className="tabular">{row.as_of?.slice(0, 10) ?? "Unavailable"}</span> },
                  { key: "type", header: "Type", render: (row) => row.trade_type ?? "Unavailable" },
                  { key: "completeness", header: "Completeness", sortValue: (row) => row.completeness ?? "", render: (row) => <Completeness value={row.completeness} /> },
                  { key: "source", header: "Source", render: (row) => (row.fixture ? <ProvenanceBadge kind="FIXTURE" /> : <ProvenanceBadge kind="EXPLORATORY" />) },
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
            ) : null}
          </Panel>
          <Panel title="Look up a job" subtitle="GET /api/v1/jobs/{job_id}. Job ids appear on the scanner after a submission.">
            <form
              className="flex flex-wrap items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                void find();
              }}
            >
              <TextInput label="Job id" value={jobId} onChange={(event) => setJobId(event.target.value)} className="w-80" />
              <Button type="submit">Look up</Button>
            </form>
            {lookup.state === "loading" ? <Skeleton rows={1} /> : null}
            {lookup.state === "error" ? <p className="text-[12px] text-[var(--gtf-fail)]">{lookup.message}</p> : null}
            {lookup.state === "ready" ? (
              <KeyValue
                columns={2}
                rows={[
                  ["Job", <span className="code">{lookup.job.job_id}</span>],
                  ["Kind", lookup.job.kind ?? <Unavailable />],
                  ["State", <JobState state={lookup.job.state} />],
                  ["Completeness", <Completeness value={lookup.job.completeness} />],
                  ["Progress", lookup.job.progress ? `${lookup.job.progress.done ?? "?"} of ${lookup.job.progress.total ?? "?"} ${lookup.job.progress.unit ?? ""}` : <Unavailable />],
                  ["Result", lookup.job.result_ref ?? <Unavailable />],
                  ["Error", lookup.job.error ? `${lookup.job.error.code}: ${lookup.job.error.message}` : "None"],
                ]}
              />
            ) : null}
          </Panel>
        </>
      ) : null}
    </Page>
  );
}

function JobPanel(props: { title: string; job: OverviewJob | null; loading: boolean; empty: string }) {
  return (
    <Panel title={props.title}>
      {props.loading ? <Skeleton rows={2} /> : null}
      {!props.loading && !props.job ? <p className="text-[12.5px] text-muted">{props.empty}</p> : null}
      {props.job ? (
        <KeyValue
          rows={[
            ["Job", props.job.job_id ? <span className="code">{props.job.job_id}</span> : <Unavailable />],
            ["State", <JobState state={props.job.state} />],
            ["Error", props.job.error_code ? `${props.job.error_code}: ${props.job.error_message ?? ""}` : "None"],
            ["Result", props.job.result_ref ?? <Unavailable />],
          ]}
        />
      ) : null}
    </Panel>
  );
}
