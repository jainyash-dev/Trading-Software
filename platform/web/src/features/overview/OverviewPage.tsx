import { useEffect, useState } from "react";
import { Button, EmptyState, Skeleton, Unavailable } from "../../design/components";
import { connectionLabel, sessionLabel } from "../../services/connection";
import { isoDate } from "../../services/idempotency";
import { useAppState } from "../../state/store";
import type {
  ApiErrorBody,
  CalendarData,
  DatasetsData,
  OverviewData,
  ScanListData,
  ScanSummary,
  UniverseData,
  Watchlist,
} from "../../types/contracts";
import { CodeList, Completeness, ErrorLine, Fact, FactGrid, Section, Value, Warning } from "../shared/ui";
import { CANDIDATE_STATUSES, numericField, statusCount } from "./model";
import { OverviewKpis, RecentTradeActivity } from "./OverviewSummary";

type Slot<T> = { state: "loading" } | { state: "ready"; data: T; fixture: boolean } | { state: "error"; error: ApiErrorBody };

function loading<T>(): Slot<T> {
  return { state: "loading" };
}

export function OverviewPage() {
  const app = useAppState();
  const request = app.request;
  const reportFailure = app.reportFailure;
  const noteFixture = app.noteFixture;
  const [overview, setOverview] = useState<Slot<OverviewData>>(loading);
  const [datasets, setDatasets] = useState<Slot<DatasetsData>>(loading);
  const [universe, setUniverse] = useState<Slot<UniverseData>>(loading);
  const [calendar, setCalendar] = useState<Slot<CalendarData>>(loading);
  const [scans, setScans] = useState<Slot<ScanListData>>(loading);
  const [watchlists, setWatchlists] = useState<Slot<{ watchlists?: Watchlist[] }>>(loading);
  const [showFixtures, setShowFixtures] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const live = app.connection === "connected";
  const day = isoDate(app.health?.last_scan?.as_of) ?? isoDate(app.health?.last_successful_ingest_date);

  useEffect(() => {
    if (!live) return;
    const controller = new AbortController();
    let active = true;
    setOverview(loading());
    setDatasets(loading());
    setUniverse(loading());
    setCalendar(loading());
    setScans(loading());
    setWatchlists(loading());
    const load = async <T,>(path: string, query?: Record<string, string | number | boolean>) => {
      try {
        const result = await request<T>(path, { query, signal: controller.signal });
        if (!active) return { state: "loading" } as Slot<T>;
        if (!result.ok) {
          reportFailure(result);
          return { state: "error", error: result.error } as Slot<T>;
        }
        return { state: "ready", data: result.envelope.data, fixture: result.envelope.meta.fixture } as Slot<T>;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return { state: "loading" } as Slot<T>;
        return {
          state: "error",
          error: { code: "DISCONNECTED", message: "Local API is not reachable", details: {} },
        } as Slot<T>;
      }
    };
    void load<OverviewData>("/api/v1/overview", day ? { as_of: day } : undefined).then((slot) => active && setOverview(slot));
    void load<DatasetsData>("/api/v1/datasets").then((slot) => active && setDatasets(slot));
    if (day) {
      void load<UniverseData>("/api/v1/universe", { as_of: day }).then((slot) => active && setUniverse(slot));
      void load<CalendarData>("/api/v1/calendar", { date: day }).then((slot) => active && setCalendar(slot));
    } else {
      setUniverse({ state: "error", error: { code: "NOT_SUPPLIED", message: "No session date was returned", details: {} } });
      setCalendar({ state: "error", error: { code: "NOT_SUPPLIED", message: "No session date was returned", details: {} } });
    }
    void load<ScanListData>("/api/v1/scans", { limit: 8, ...(showFixtures ? { include_fixtures: true } : {}) }).then(
      (slot) => active && setScans(slot),
    );
    void load<{ watchlists?: Watchlist[] }>("/api/v1/watchlists").then((slot) => active && setWatchlists(slot));
    return () => {
      active = false;
      controller.abort();
    };
  }, [live, day, showFixtures, reloadKey, app.revision, request, reportFailure]);

  const fixture =
    (overview.state === "ready" && overview.fixture) ||
    (datasets.state === "ready" && datasets.fixture) ||
    (scans.state === "ready" && scans.fixture) ||
    (datasets.state === "ready" && (datasets.data.datasets ?? []).some((row) => row.fixture === true));

  useEffect(() => {
    noteFixture("overview", fixture);
    return () => noteFixture("overview", false);
  }, [noteFixture, fixture]);

  const health = live ? app.health : null;
  const dataReady = health && typeof health.data_ready === "boolean" ? health.data_ready : null;
  const lastScan = health?.last_scan ?? null;
  const successful = lastScan && lastScan.completeness === "COMPLETE" ? lastScan : null;
  const limitations = [
    ...(health?.data_limitations ?? []),
    ...(datasets.state === "ready" ? datasets.data.limitations ?? [] : []),
    ...(universe.state === "ready" ? universe.data.limitations ?? [] : []),
  ].filter((code, index, all) => all.indexOf(code) === index);
  const counts = overview.state === "ready" ? overview.data.counts ?? null : undefined;
  const scanRows = scans.state === "ready" ? scans.data.scans ?? [] : [];
  const accepted = scanRows.filter((row) => row.fixture !== true);
  const fixtures = scanRows.filter((row) => row.fixture === true);
  const lists = watchlists.state === "ready" ? watchlists.data.watchlists ?? [] : [];

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-4 px-5 py-4">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3">
        <div>
          <p className="eyebrow">Overview</p>
          <h1 className="mt-0.5 text-[19px] font-semibold leading-6 tracking-[-0.01em]">Market Overview</h1>
          <p className="mt-1 max-w-4xl text-[12.5px] leading-[1.5] text-muted">
            Platform, data, universe, and the latest stored research. Counts come from the API. A missing scan is not a zero.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="primary" onClick={() => app.navigate("scanner")}>
            Create a scan
          </Button>
          <Button type="button" onClick={() => app.navigate("scanner", { panel: "history" })}>
            Open scan history
          </Button>
          <Button type="button" onClick={() => app.navigate("opportunities")}>
            Opportunities
          </Button>
          <Button type="button" onClick={() => app.navigate("watchlists")}>
            Manage watchlists
          </Button>
          <Button type="button" onClick={() => app.navigate("data")}>
            Inspect data status
          </Button>
        </div>
      </header>

      {live ? <OverviewKpis /> : null}

      {!live ? (
        <EmptyState
          title={connectionLabel(app.connection)}
          reason="Overview figures stay hidden until the API session responds. A rendered page is not a health check."
        />
      ) : null}

      <Section
        title="Latest scan"
        action={
          lastScan ? (
            <Button type="button" onClick={() => app.navigate("scanner", { scan: lastScan.scan_key })}>
              Inspect the latest scan
            </Button>
          ) : null
        }
      >
        {!lastScan ? (
          <EmptyState title="No non-fixture scan is stored" reason="Health returned no last scan. Fixture runs are excluded from this card." />
        ) : (
          <FactGrid>
            <Fact label="Scan">{lastScan.scan_key}</Fact>
            <Fact label="As of">{lastScan.as_of}</Fact>
            <Fact label="Dataset">{lastScan.dataset_id || <Unavailable />}</Fact>
            <Fact label="Completeness">
              <Completeness value={lastScan.completeness} />
            </Fact>
            <Fact label="Job state">{live && overview.state === "ready" && overview.data.job?.state ? overview.data.job.state : <Unavailable />}</Fact>
            <Fact label="Active job">
              {live && overview.state === "ready" && overview.data.active_job?.state ? overview.data.active_job.state : <Unavailable />}
            </Fact>
            <Fact label="Job phase">
              {live && overview.state === "ready" && overview.data.job_phase ? overview.data.job_phase : <Unavailable />}
            </Fact>
            <Fact label="Scan due">
              {live && overview.state === "ready" && overview.data.scan_due?.state ? (
                <span>
                  {overview.data.scan_due.state}
                  {overview.data.scan_due.as_of ? ` · ${overview.data.scan_due.as_of}` : ""}
                  {overview.data.scan_due.reason ? ` · ${overview.data.scan_due.reason}` : ""}
                </span>
              ) : (
                <Unavailable />
              )}
            </Fact>
            <Fact label="Readiness">
              {live && overview.state === "ready" && overview.data.readiness_state ? overview.data.readiness_state : <Unavailable />}
            </Fact>
            <Fact label="Manifest">{live && overview.state === "ready" && overview.data.manifest_id ? overview.data.manifest_id : <Unavailable />}</Fact>
            <Fact label="Full universe">{live && overview.state === "ready" ? String(overview.data.full_universe_scan === true) : <Unavailable />}</Fact>
            <Fact label="Latest successful scan">{successful ? successful.scan_key : <Unavailable />}</Fact>
          </FactGrid>
        )}
        {live && overview.state === "ready" && overview.data.active_job?.state ? (
          <Warning>A job is {overview.data.active_job.state}. It is not a completed scan.</Warning>
        ) : null}
        {lastScan?.completeness === "PARTIAL" ? <Warning>This scan is PARTIAL. It is not a complete scan.</Warning> : null}
        {lastScan?.completeness === "FAILED" ? <Warning>This scan FAILED. It is not a successful scan.</Warning> : null}
        {live && overview.state === "ready" && overview.data.certified_p0_data === true ? (
          <Warning>certified_p0_data is true on this payload. Confirm P0 evidence before treating the universe as certified.</Warning>
        ) : null}
        {live && overview.state === "ready" && overview.data.history_cut?.applied ? (
          <Warning>History starts after an unresolved calendar date for {overview.data.history_cut.symbols?.join(", ") || "one or more symbols"}. Earlier candles are not used.</Warning>
        ) : null}
        {live && overview.state === "ready" && overview.data.identity_findings && overview.data.identity_findings.length > 0 ? (
          <Warning>Unresolved ISIN splits stay unjoined: {overview.data.identity_findings.join(", ")}.</Warning>
        ) : null}
        {live && overview.state === "ready" && overview.data.data_ready === false ? (
          <Warning>{overview.data.data_ready_reason || "DATA_READY is not claimed."}</Warning>
        ) : null}
        <div>
          <h3 className="mb-2 text-[12px] font-semibold">Candidate counts</h3>
          <FactGrid>
            {CANDIDATE_STATUSES.map((status) => {
              const value = live && overview.state === "ready" ? statusCount(counts, status) : null;
              return (
                <Fact key={status} label={status}>
                  <span aria-label={`${status} candidate count`} data-count={value === null ? "unavailable" : String(value)}>
                    {value === null ? <Unavailable /> : <span className="tabular">{value}</span>}
                  </span>
                </Fact>
              );
            })}
          </FactGrid>
          <p className="mt-2 text-[11px] text-muted">
            Stored symbols {live && overview.state === "ready" && counts ? <Value value={numericField(counts.symbols)} /> : <Unavailable />}. Index{" "}
            <span data-testid="index-value">
              {overview.state === "ready" && overview.data.index != null ? <Value value={overview.data.index} /> : <Unavailable />}
            </span>
            . Sector{" "}
            <span data-testid="sector-value">
              {overview.state === "ready" && overview.data.sector != null ? <Value value={overview.data.sector} /> : <Unavailable />}
            </span>
            . Breadth{" "}
            <span data-testid="breadth-value">
              {overview.state === "ready" && overview.data.breadth != null ? <Value value={overview.data.breadth} /> : <Unavailable />}
            </span>
            .
          </p>
        </div>
      </Section>

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
      <Section id="data-status" title="Data readiness">
        {live && health?.readiness_state ? (
          <FactGrid>
            <Fact label="Readiness state">
              <Value value={health.readiness_state} />
            </Fact>
            <Fact label="certified_p0_data">
              <Value value={health.certified_p0_data === true} />
            </Fact>
          </FactGrid>
        ) : null}
        {dataReady === false ? <Warning>data_ready is false. DATA_READY is not claimed.</Warning> : null}
        {dataReady === true ? <Warning>data_ready is true on this payload. Other limitations below still apply.</Warning> : null}
        {dataReady === null ? (
          <p className="text-[12px]">
            data_ready <Unavailable />
          </p>
        ) : null}
        {datasets.state === "loading" && live ? <Skeleton rows={2} /> : null}
        {datasets.state === "error" ? <ErrorLine error={datasets.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
        {datasets.state === "ready" && (datasets.data.datasets ?? []).length === 0 ? (
          <EmptyState title="No dataset" reason="The datasets route returned no dataset id." />
        ) : null}
        {datasets.state === "ready"
          ? (datasets.data.datasets ?? []).map((row) => (
              <article key={row.dataset_id ?? "dataset"} className="border border-line px-3 py-2">
                <FactGrid>
                  <Fact label="Dataset" testId="dataset-id">
                    <Value value={row.dataset_id} />
                  </Fact>
                  <Fact label="Manifest hash">
                    <Value value={row.manifest_sha256} />
                  </Fact>
                  <Fact label="Research validation">
                    <Value value={row.research_validation} />
                  </Fact>
                  <Fact label="Dataset data_ready">
                    <Value value={row.data_ready} />
                  </Fact>
                  <Fact label="Files">
                    <Value value={row.file_count} />
                  </Fact>
                  <Fact label="Dataset fixture">{row.fixture === true ? "FIXTURE_NOT_MARKET_DATA" : <Value value={row.fixture} />}</Fact>
                </FactGrid>
              </article>
            ))
          : null}
        <FactGrid>
          <Fact label="Latest session date">{live ? <Value value={health?.last_successful_ingest_date} /> : <Unavailable />}</Fact>
          <Fact label="Calendar">
            {calendar.state === "ready" ? (
              <span>
                {calendar.data.status ?? "Unavailable"}
                {calendar.data.classification ? ` · ${calendar.data.classification}` : ""}
                {calendar.data.reason ? ` · ${calendar.data.reason}` : ""}
              </span>
            ) : calendar.state === "error" ? (
              <span>
                {calendar.error.code}: {calendar.error.message}
              </span>
            ) : (
              <Unavailable />
            )}
          </Fact>
        </FactGrid>
        <div>
          <h3 className="text-[12px] font-semibold">Data-quality warnings</h3>
          <div className="mt-1 text-[12px]">
            {live && datasets.state !== "loading" && universe.state !== "loading" ? <CodeList codes={limitations} /> : <Unavailable />}
          </div>
        </div>
      </Section>
        <div className="space-y-4">
      <Section title="Platform status">
        <FactGrid>
          <Fact label="API connection">{connectionLabel(app.connection)}</Fact>
          <Fact label="Session">{sessionLabel(app.connection)}</Fact>
          <Fact label="Application status">{live ? <Value value={health?.outcome} /> : <Unavailable />}</Fact>
          <Fact label="Scheduler">{live ? <Value value={health?.scheduler_state} /> : <Unavailable />}</Fact>
          <Fact label="Platform database">
            {live ? reachability(health?.database_files?.platform?.reachable) : <Unavailable />}
          </Fact>
          <Fact label="Research database">
            {live ? reachability(health?.database_files?.research?.reachable) : <Unavailable />}
          </Fact>
          <Fact label="Last ingest date">{live ? <Value value={health?.last_successful_ingest_date} /> : <Unavailable />}</Fact>
          <Fact label="orders_placed">{live ? <Value value={health?.orders_placed} /> : <Unavailable />}</Fact>
        </FactGrid>
      </Section>
      <Section title="Universe status">
        {universe.state === "loading" && live ? <Skeleton rows={2} /> : null}
        {universe.state === "error" ? <ErrorLine error={universe.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
        {universe.state === "ready" ? (
          <FactGrid>
            <Fact label="Supported universe">
              <Value value={universe.data.name} />
            </Fact>
            <Fact label="Certified">
              <Value value={universe.data.certified} />
            </Fact>
            <Fact label="Universe size">
              {Array.isArray(universe.data.members) ? <span className="tabular">{universe.data.members.length}</span> : <Unavailable />}
            </Fact>
            <Fact label="full_universe_scan">
              <Value value={universe.data.full_universe_scan} />
            </Fact>
          </FactGrid>
        ) : null}
        <div className="text-[12px]">
          <CodeList codes={universe.state === "ready" ? universe.data.limitations : undefined} />
        </div>
        <p className="text-[12px] text-muted">Nifty 100 is not described as certified. Nifty 50 historical membership is not claimed.</p>
      </Section>
        </div>
      </div>

      <Section
        id="research-activity"
        title="Research activity"
        action={
          <Button type="button" onClick={() => setShowFixtures((value) => !value)}>
            {showFixtures ? "Hide fixture scans" : "Show fixture scans"}
          </Button>
        }
      >
        {scans.state === "loading" && live ? <Skeleton rows={3} /> : null}
        {scans.state === "error" ? <ErrorLine error={scans.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
        {scans.state === "ready" && accepted.length === 0 ? (
          <EmptyState title="No accepted-data scans" reason="The scan history has no non-fixture row." action="Create a scan from the scanner." />
        ) : null}
        {accepted.length > 0 ? <ScanTable rows={accepted} onOpen={(key) => app.navigate("scanner", { scan: key })} /> : null}
        {showFixtures ? (
          <div className="space-y-2">
            <p className="text-[12px] font-semibold">FIXTURE_NOT_MARKET_DATA</p>
            {fixtures.length === 0 ? (
              <EmptyState title="No fixture scans" reason="The history request included fixtures and none were returned." />
            ) : (
              <ScanTable rows={fixtures} onOpen={(key) => app.navigate("scanner", { scan: key, fixtures: "1" })} />
            )}
          </div>
        ) : null}
      </Section>

      {live ? <RecentTradeActivity /> : null}

      <div className="grid items-start gap-4 xl:grid-cols-2">
      <Section title="Watchlists">
        {watchlists.state === "loading" && live ? <Skeleton rows={2} /> : null}
        {watchlists.state === "error" ? <ErrorLine error={watchlists.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
        {watchlists.state === "ready" && lists.length === 0 ? (
          <EmptyState title="No watchlist is stored" reason="A watchlist is an organisational list, not a qualified opportunity." />
        ) : null}
        {lists.length > 0 ? (
          <ul className="divide-y divide-line rounded-[4px] border border-line">
            {lists.map((list) => (
              <li key={list.watchlist_id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-[12px]">
                <span>
                  <span className="font-semibold">{list.name}</span>
                  <span className="text-muted">
                    {" "}
                    · {Array.isArray(list.symbols) ? `${list.symbols.length} symbols` : "symbol count unavailable"}
                  </span>
                </span>
                <Button type="button" onClick={() => app.navigate("watchlists", { watchlist: list.watchlist_id })}>
                  Open {list.name}
                </Button>
              </li>
            ))}
          </ul>
        ) : null}
        <p className="text-[11px] text-muted">Watchlist membership is not a trading signal and is not a qualified result.</p>
      </Section>
      <Section title="What to investigate next">
        <ul className="list-disc space-y-1 pl-4 text-[12px]">
          {dataReady === false ? <li>Review data status. data_ready is false.</li> : null}
          {limitations.includes("UNIVERSE_UNVERIFIED") ? <li>Universe verification is UNIVERSE_UNVERIFIED.</li> : null}
          {!lastScan ? <li>No stored non-fixture scan. Create a scan when a dataset id is available.</li> : null}
          {lastScan?.completeness === "PARTIAL" ? <li>The latest scan is partial. Inspect it before treating the run as complete.</li> : null}
          {lastScan?.completeness === "FAILED" ? <li>The latest scan failed. Inspect the stored result.</li> : null}
          {watchlists.state === "ready" && lists.length === 0 ? <li>No watchlist is stored.</li> : null}
          {health?.outcome === "FAIL" ? <li>Application status is FAIL.</li> : null}
        </ul>
      </Section>
      </div>
    </section>
  );
}

function reachability(value: boolean | undefined) {
  if (value === true) return "reachable";
  if (value === false) return "not reachable";
  return <Unavailable />;
}

function ScanTable(props: { rows: ScanSummary[]; onOpen: (scanKey: string) => void }) {
  return (
    <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
      <table className="gtf-table w-full border-collapse text-left text-[12px]">
        <thead className="bg-surface-2">
          <tr>
            {["Scan", "Type", "As of", "Completeness", "Dataset", "Fixture", ""].map((header) => (
              <th key={header || "open"} className="border-b border-line px-2 py-2 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row) => (
            <tr key={row.scan_key} className="h-9">
              <td className="border-b border-line px-2">{row.scan_key}</td>
              <td className="border-b border-line px-2">{row.trade_type ?? "Unavailable"}</td>
              <td className="border-b border-line px-2">{row.as_of ?? "Unavailable"}</td>
              <td className="border-b border-line px-2">
                <Completeness value={row.completeness} />
              </td>
              <td className="border-b border-line px-2">{row.dataset_id ?? "Unavailable"}</td>
              <td className="border-b border-line px-2">{row.fixture ? "FIXTURE_NOT_MARKET_DATA" : "false"}</td>
              <td className="border-b border-line px-2">
                <Button type="button" onClick={() => props.onOpen(row.scan_key)}>
                  Inspect
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
