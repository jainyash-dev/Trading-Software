import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Checkbox,
  Dialog,
  EmptyState,
  Page,
  SelectInput,
  Skeleton,
  StatusBadge,
  TextInput,
  Unavailable,
} from "../../design/components";
import { connectionLabel } from "../../services/connection";
import { useAppState } from "../../state/store";
import type { ApiErrorBody, Opportunity, OpportunityListData, ScanListData, Watchlist } from "../../types/contracts";
import { ErrorLine, Fact, FactGrid, Section, Warning } from "../shared/ui";

const WORKFLOWS = [
  "",
  "DISCOVERED",
  "UNDER_REVIEW",
  "SHORTLISTED",
  "REJECTED",
  "EXPIRED",
  "BLOCKED",
  "ARCHIVED",
] as const;

type Slot<T> = { state: "loading" } | { state: "ready"; data: T; fixture: boolean } | { state: "error"; error: ApiErrorBody };

export function OpportunitiesPage() {
  const app = useAppState();
  const request = app.request;
  const reportFailure = app.reportFailure;
  const noteFixture = app.noteFixture;
  const connected = app.connection === "connected";
  const query = new URLSearchParams(app.queryString);
  const [slot, setSlot] = useState<Slot<OpportunityListData>>({ state: "loading" });
  const [scans, setScans] = useState<ScanListData | null>(null);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [selectedScan, setSelectedScan] = useState(query.get("scan") || "");
  const [workflow, setWorkflow] = useState(query.get("workflow") || "");
  const [search, setSearch] = useState(query.get("q") || "");
  const [watchlistId, setWatchlistId] = useState(query.get("watchlist") || "");
  const [includeFixtures, setIncludeFixtures] = useState(query.get("fixtures") === "1");
  const [sort, setSort] = useState(query.get("sort") || "priority");
  const [reloadKey, setReloadKey] = useState(0);
  const [ingesting, setIngesting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState<{ id: string; to: string; reasonRequired: boolean } | null>(null);
  const [reason, setReason] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!connected) return;
    const controller = new AbortController();
    let active = true;
    setSlot({ state: "loading" });
    const params: Record<string, string | number | boolean> = {
      sort,
      include_fixtures: includeFixtures,
      limit: 200,
    };
    if (workflow) params.workflow_state = workflow;
    if (search.trim()) params.q = search.trim();
    if (watchlistId) params.watchlist_id = watchlistId;
    if (selectedScan) params.scan_key = selectedScan;
    void request<OpportunityListData>("/api/v1/opportunities", { query: params, signal: controller.signal }).then((result) => {
      if (!active) return;
      if (!result.ok) {
        reportFailure(result);
        setSlot({ state: "error", error: result.error });
        return;
      }
      noteFixture("opportunities", result.envelope.meta.fixture);
      setSlot({ state: "ready", data: result.envelope.data, fixture: result.envelope.meta.fixture });
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [connected, workflow, search, watchlistId, selectedScan, includeFixtures, sort, reloadKey, request, reportFailure, noteFixture]);

  useEffect(() => {
    if (!connected) return;
    const controller = new AbortController();
    let active = true;
    void request<ScanListData>("/api/v1/scans", {
      query: { limit: 20, ...(includeFixtures ? { include_fixtures: true } : {}) },
      signal: controller.signal,
    }).then((result) => {
      if (!active || !result.ok) return;
      setScans(result.envelope.data);
    });
    void request<{ watchlists?: Watchlist[] }>("/api/v1/watchlists", { signal: controller.signal }).then((result) => {
      if (!active || !result.ok) return;
      setWatchlists(result.envelope.data.watchlists ?? []);
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [connected, includeFixtures, request, reloadKey]);

  const rows = slot.state === "ready" ? slot.data.opportunities ?? [] : [];
  const selected = useMemo(() => rows.find((row) => row.opportunity_id === selectedId) ?? null, [rows, selectedId]);
  const counts = slot.state === "ready" ? slot.data.counts_by_workflow ?? {} : {};

  async function ingest() {
    if (!selectedScan) {
      setFormError("Choose a stored scan to ingest.");
      return;
    }
    setIngesting(true);
    setFormError(null);
    const result = await request("/api/v1/opportunities/ingest", {
      method: "POST",
      body: { scan_key: selectedScan, include_rejected: true },
    });
    setIngesting(false);
    if (!result.ok) {
      reportFailure(result);
      setFormError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    setReloadKey((value) => value + 1);
  }

  async function transition(id: string, toState: string, transitionReason: string) {
    const result = await request<Opportunity>(`/api/v1/opportunities/${encodeURIComponent(id)}/transition`, {
      method: "POST",
      body: { to_state: toState, ...(transitionReason ? { reason: transitionReason } : {}) },
    });
    if (!result.ok) {
      reportFailure(result);
      setFormError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    setPending(null);
    setReason("");
    setReloadKey((value) => value + 1);
    setSelectedId(id);
  }

  function openAnalysis(row: Opportunity) {
    if (!row.scan_key || !row.symbol) return;
    app.navigate("analysis", {
      scan: row.scan_key,
      symbol: row.symbol,
      ...(row.as_of ? { as_of: row.as_of.slice(0, 10) } : {}),
      ...(row.dataset_id ? { dataset_id: row.dataset_id } : {}),
      ...(row.timeframe === "M" || row.timeframe === "W" || row.timeframe === "D" ? { timeframe: row.timeframe } : {}),
      ...(row.zone_id ? { zone: row.zone_id } : {}),
      ...(row.fixture ? { fixtures: "1" } : {}),
    });
  }

  function syncQuery(patch: Record<string, string | null>) {
    app.navigate("opportunities", {
      ...(selectedScan ? { scan: selectedScan } : {}),
      ...(workflow ? { workflow } : {}),
      ...(search ? { q: search } : {}),
      ...(watchlistId ? { watchlist: watchlistId } : {}),
      ...(includeFixtures ? { fixtures: "1" } : {}),
      ...(sort && sort !== "priority" ? { sort } : {}),
      ...patch,
    });
  }

  return (
    <Page
      title="Opportunities"
      description="Research organisation over stored scanner candidates. Workflow state does not change GTF eligibility. Organizational priority does not predict returns."
      actions={
        <Button type="button" onClick={() => app.navigate("scanner")}>
          Open scanner
        </Button>
      }
    >
      {!connected ? (
        <EmptyState title={connectionLabel(app.connection)} reason="Opportunity records stay on the platform database." />
      ) : null}
      <Warning>
        P0 certification is incomplete. Non-fixture local rows remain exploratory. Fixture rows are not market opportunities.
      </Warning>
      {slot.state === "ready" && slot.data.limitation ? <p className="text-[12px] text-muted">{slot.data.limitation}</p> : null}
      {slot.state === "ready" && slot.data.priority_disclosure ? (
        <p className="text-[12px] text-muted">{slot.data.priority_disclosure}</p>
      ) : null}
      {formError ? <p className="text-[12px]">{formError}</p> : null}
      {slot.state === "error" ? <ErrorLine error={slot.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}

      <Section title="Attention">
        <FactGrid>
          <Fact label="Discovered">{counts.DISCOVERED ?? 0}</Fact>
          <Fact label="Under review">{counts.UNDER_REVIEW ?? 0}</Fact>
          <Fact label="Shortlisted">{counts.SHORTLISTED ?? 0}</Fact>
          <Fact label="Blocked">{counts.BLOCKED ?? 0}</Fact>
          <Fact label="Rejected">{counts.REJECTED ?? 0}</Fact>
          <Fact label="Expired">{counts.EXPIRED ?? 0}</Fact>
          <Fact label="Archived">{counts.ARCHIVED ?? 0}</Fact>
        </FactGrid>
      </Section>

      <Section title="Ingest stored scan">
        <div className="flex flex-wrap items-end gap-2">
          <SelectInput
            label="Stored scan"
            value={selectedScan}
            onChange={(event) => {
              setSelectedScan(event.target.value);
              syncQuery({ scan: event.target.value || null });
            }}
          >
            <option value="">Select a scan</option>
            {(scans?.scans ?? []).map((scan) => (
              <option key={scan.scan_key} value={scan.scan_key}>
                {scan.scan_key}
                {scan.fixture ? " (fixture)" : ""} · {scan.as_of ?? "as_of unavailable"}
              </option>
            ))}
          </SelectInput>
          <Button type="button" disabled={!connected || ingesting || !selectedScan} onClick={() => void ingest()}>
            Ingest candidates
          </Button>
          <Checkbox
            label="Include fixture scans / rows"
            checked={includeFixtures}
            onChange={(checked) => {
              setIncludeFixtures(checked);
              syncQuery({ fixtures: checked ? "1" : null });
            }}
          />
        </div>
      </Section>

      <Section title="Filters">
        <p className="text-[12px] text-muted">Watchlist membership filters the desk list only. It is not universe membership and does not imply GTF eligibility.</p>
        <div className="flex flex-wrap items-end gap-2">
          <TextInput
            label="Search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onBlur={() => syncQuery({ q: search.trim() || null })}
          />
          <SelectInput
            label="Workflow"
            value={workflow}
            onChange={(event) => {
              setWorkflow(event.target.value);
              syncQuery({ workflow: event.target.value || null });
            }}
          >
            {WORKFLOWS.map((value) => (
              <option key={value || "all"} value={value}>
                {value || "All workflows"}
              </option>
            ))}
          </SelectInput>
          <SelectInput
            label="Watchlist"
            value={watchlistId}
            onChange={(event) => {
              setWatchlistId(event.target.value);
              syncQuery({ watchlist: event.target.value || null });
            }}
          >
            <option value="">Any watchlist</option>
            {watchlists.map((list) => (
              <option key={list.watchlist_id} value={list.watchlist_id}>
                {list.name}
              </option>
            ))}
          </SelectInput>
          <SelectInput
            label="Sort"
            value={sort}
            onChange={(event) => {
              setSort(event.target.value);
              syncQuery({ sort: event.target.value === "priority" ? null : event.target.value });
            }}
          >
            <option value="priority">Organizational priority</option>
            <option value="symbol">Symbol</option>
            <option value="discovered">Discovered</option>
            <option value="updated">Updated</option>
          </SelectInput>
        </div>
      </Section>

      {connected && slot.state === "loading" ? <Skeleton rows={5} /> : null}
      {connected && slot.state === "ready" && rows.length === 0 ? (
        <EmptyState
          title="No opportunities match"
          reason="Ingest a stored scan, or clear filters. Nothing here is a buy recommendation."
          action="Scanner remains the place to run research. This page only organises stored results."
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="grid items-start gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
          <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
            <table className="gtf-table w-full border-collapse text-left text-[12px]">
              <thead>
                <tr>
                  {["Symbol", "Workflow", "Canonical status", "Quality", "TF", "Priority", ""].map((header) => (
                    <th key={header || "actions"} className="border-b border-line px-2 py-2 font-medium">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.opportunity_id}
                    className={row.opportunity_id === selectedId ? "bg-[var(--gtf-neutral-bg)]" : undefined}
                    onClick={() => setSelectedId(row.opportunity_id)}
                  >
                    <td className="border-b border-line px-2 py-2 font-medium">{row.symbol}</td>
                    <td className="border-b border-line px-2 py-2">{row.workflow_state}</td>
                    <td className="border-b border-line px-2 py-2">
                      <StatusBadge code={row.canonical_status} />
                    </td>
                    <td className="border-b border-line px-2 py-2">
                      {row.fixture ? "FIXTURE" : row.source_quality}
                    </td>
                    <td className="border-b border-line px-2 py-2">{row.timeframe || <Unavailable />}</td>
                    <td className="border-b border-line px-2 py-2 tabular">{row.organizational_priority?.score ?? <Unavailable />}</td>
                    <td className="border-b border-line px-2 py-2">
                      <Button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          openAnalysis(row);
                        }}
                      >
                        Analysis
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Section title="Selected opportunity">
            {!selected ? <EmptyState title="Nothing selected" reason="Choose a row to review workflow and provenance." /> : null}
            {selected ? (
              <div className="space-y-3">
                <FactGrid>
                  <Fact label="Symbol">{selected.symbol}</Fact>
                  <Fact label="Scan">{selected.scan_key}</Fact>
                  <Fact label="Zone">{selected.zone_id || <Unavailable />}</Fact>
                  <Fact label="As of">{selected.as_of || <Unavailable />}</Fact>
                  <Fact label="Source quality">{selected.fixture ? "FIXTURE_NOT_MARKET_DATA" : selected.source_quality}</Fact>
                  <Fact label="Workflow">{selected.workflow_state}</Fact>
                </FactGrid>
                <p className="text-[12px] text-muted">
                  Canonical status is a stored snapshot. Changing workflow never rewrites it and never authorises an order.
                </p>
                {["BLOCKED", "REJECTED", "DATA_INSUFFICIENT"].includes(selected.canonical_status) &&
                selected.workflow_state === "SHORTLISTED" ? (
                  <Warning>
                    Workflow is SHORTLISTED but stored canonical status is {selected.canonical_status}. That is not a GTF pass.
                  </Warning>
                ) : null}
                <StatusBadge code={selected.canonical_status} />
                {selected.source_snapshot?.manual_checks ? (
                  <p className="text-[12px]">Manual checks remain pending on the stored candidate. This page does not clear them.</p>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  {(selected.allowed_transitions ?? []).map((state) => (
                    <Button
                      key={state}
                      type="button"
                      onClick={() =>
                        setPending({
                          id: selected.opportunity_id,
                          to: state,
                          reasonRequired: state === "REJECTED" || state === "EXPIRED" || state === "ARCHIVED",
                        })
                      }
                    >
                      Move to {state}
                    </Button>
                  ))}
                  <Button type="button" onClick={() => openAnalysis(selected)}>
                    Open stock analysis
                  </Button>
                  <Button
                    type="button"
                    onClick={() =>
                      app.navigate("plans", {
                        scan: selected.scan_key,
                        symbol: selected.symbol,
                        ...(selected.zone_id ? { zone: selected.zone_id } : {}),
                      })
                    }
                  >
                    Trade planning entry
                  </Button>
                </div>
              </div>
            ) : null}
          </Section>
        </div>
      ) : null}

      {pending ? (
        <Dialog
          title={`Move to ${pending.to}`}
          body={
            pending.reasonRequired
              ? "This workflow change needs a reason. It does not change zone freshness or GTF eligibility."
              : "Confirm the workflow change. Canonical scanner status stays unchanged."
          }
          confirm="Confirm"
          onClose={() => {
            setPending(null);
            setReason("");
          }}
          onConfirm={() => {
            if (pending.reasonRequired && !reason.trim()) {
              setFormError("A reason is required for this transition.");
              return;
            }
            void transition(pending.id, pending.to, reason.trim());
          }}
        >
          {pending.reasonRequired ? (
            <TextInput label="Reason" value={reason} onChange={(event) => setReason(event.target.value)} />
          ) : null}
        </Dialog>
      ) : null}
    </Page>
  );
}
