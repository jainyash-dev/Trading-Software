import { Button, Metric, Meter, Panel, ProvenanceBadge, StatusBadge } from "../../design/components";
import { formatDate, toNumber } from "../../design/format";
import { useAppState } from "../../state/store";
import { dataOf, useApi } from "../shared/useApi";

type Row = Record<string, unknown>;

/** P10-3 status strip: data, scan, caps and health. Each figure is read from an API; none is derived. */
export function OverviewKpis() {
  const app = useAppState();
  const live = app.connection === "connected";
  const health = live ? app.health : null;
  const portfolio = useApi<Row>("/api/v1/portfolio");
  const book = dataOf(portfolio);
  const scan = health?.last_scan ?? null;
  const monthly = toNumber(book?.trades_triggered_this_month);
  const monthlyCap = toNumber(book?.monthly_cap);
  const open = toNumber(book?.open_positions);
  const openCap = toNumber(book?.open_position_cap);
  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4" aria-label="Research status summary">
      <Metric
        label="Data"
        value={live ? health?.last_successful_ingest_date ?? null : null}
        sub={
          <span className="flex flex-wrap items-center gap-1.5">
            Latest accepted EOD date
            {live ? <ProvenanceBadge kind={health?.certified_p0_data === true ? "CERTIFIED" : "PROVISIONAL"} title="certified_p0_data" /> : null}
          </span>
        }
      />
      <Metric
        label="Latest scan"
        value={scan ? scan.as_of.slice(0, 10) : null}
        tone={scan && scan.completeness !== "COMPLETE" ? "manual" : "neutral"}
        sub={scan ? `${scan.completeness} · ${scan.scan_key}` : "Run a scan to populate research"}
      />
      <Metric
        label="Monthly trades"
        value={monthly === null ? null : `${monthly} of ${monthlyCap ?? "?"}`}
        sub={book ? `Open positions ${open ?? "unavailable"} of ${openCap ?? "?"} · independent caps` : "Portfolio not read"}
      >
        {book ? <Meter value={monthly} max={monthlyCap} label="Monthly trade cap usage" /> : null}
      </Metric>
      <Metric
        label="Readiness"
        value={live ? health?.readiness_state ?? null : null}
        tone={health?.outcome === "FAIL" ? "fail" : "manual"}
        sub={live ? `Application ${health?.outcome ?? "unavailable"} · data_ready ${String(health?.data_ready ?? "unavailable")}` : "API not connected"}
      />
    </div>
  );
}

/** P10-3 recent trade activity from the plan list and the journal list. */
export function RecentTradeActivity() {
  const app = useAppState();
  const plans = useApi<{ plans?: Row[] }>("/api/v1/plans", { limit: 5 });
  const journal = useApi<{ entries?: Row[]; total?: number }>("/api/v1/journal");
  const planRows = (dataOf(plans)?.plans ?? []).slice(0, 5);
  const entryRows = (dataOf(journal)?.entries ?? []).slice(0, 5);
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel
        title="Recent trade plans"
        actions={
          <Button size="sm" type="button" onClick={() => app.navigate("plans")}>
            All plans
          </Button>
        }
      >
        {plans.state === "error" ? <p className="text-[12px] text-muted">Plans unavailable ({plans.error.code}).</p> : null}
        {plans.state === "ready" && planRows.length === 0 ? <p className="text-[12px] text-muted">No trade plan is stored.</p> : null}
        <ul className="divide-y divide-line">
          {planRows.map((row) => (
            <li key={String(row.plan_id)} className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-[12px]">
              <button type="button" className="text-left" onClick={() => app.navigate("plans", { plan: String(row.plan_id) })}>
                <span className="font-semibold text-[var(--gtf-accent)]">{String(row.symbol)}</span> <span className="text-muted">{String(row.state)}</span>
              </button>
              <span className="flex items-center gap-2">
                <StatusBadge code={String(row.candidate_status)} />
                <span className="tabular text-muted">{formatDate(row.created_at) ?? ""}</span>
              </span>
            </li>
          ))}
        </ul>
      </Panel>
      <Panel
        title="Recent journal entries"
        actions={
          <Button size="sm" type="button" onClick={() => app.navigate("journal")}>
            Journal
          </Button>
        }
      >
        {journal.state === "error" ? <p className="text-[12px] text-muted">Journal unavailable ({journal.error.code}).</p> : null}
        {journal.state === "ready" && entryRows.length === 0 ? <p className="text-[12px] text-muted">No journal entry. An approved plan creates the first row.</p> : null}
        <ul className="divide-y divide-line">
          {entryRows.map((row) => (
            <li key={String(row.entry_id)} className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-[12px]">
              <button type="button" className="text-left" onClick={() => app.navigate("journal", { entry: String(row.entry_id) })}>
                <span className="font-semibold text-[var(--gtf-accent)]">{String(row.symbol)}</span> <span className="text-muted">entry {String(row.entry_id)}</span>
              </button>
              <span className="text-muted">
                {String(row.state)} · review {String((row.review as { review_status?: unknown } | undefined)?.review_status ?? "NOT_REVIEWED")}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
