import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, Dialog, EmptyState, KeyValue, Page, Panel, ProvenanceBadge, StatusBadge, TextInput, Unavailable } from "../../design/components";
import { formatDate, formatInr, formatPrice, formatQuantity, text } from "../../design/format";
import { readViewQuery } from "../../navigation/query";
import { useAppState } from "../../state/store";
import { Warning } from "../shared/ui";

const PLAN_CHECKLIST = [
  "EXPLOSIVE_RELATIVE_SIZE_CONTEXT",
  "GAP_MEANINGFULNESS",
  "AUTHENTICITY",
  "GARBAGE_CHART",
  "LOTL",
  "CAME_FROM",
  "TARGET_QUALITY",
  "BUFFER_SELECTION",
  "SECTOR",
  "CORPORATE_ACTIONS",
  "TRADER_STATE",
] as const;

const STATES = [
  ["DRAFT", "Drafts"],
  ["AWAITING_OWNER", "Awaiting review"],
  ["APPROVED", "Approved"],
  ["REJECTED", "Rejected"],
  ["CANCELLED", "Cancelled"],
  ["EXPIRED", "Expired"],
] as const;

type Row = Record<string, unknown>;

/**
 * P10-6 Trade Plans. Every action calls the existing P4 plan routes. A plan copies a stored
 * candidate; the journal is the canonical execution record. Approval never places an order.
 */
export function PlansPage() {
  const app = useAppState();
  const view = useMemo(() => readViewQuery(app.queryString), [app.queryString]);
  const [scanKey, setScanKey] = useState(view.scan);
  const [symbol, setSymbol] = useState(view.symbol);
  const [zoneId, setZoneId] = useState(view.zone);
  const [filterState, setFilterState] = useState(view.planState);
  const [rationale, setRationale] = useState("");
  useEffect(() => {
    setScanKey(view.scan);
    setSymbol(view.symbol);
    setZoneId(view.zone);
    setFilterState(view.planState);
  }, [view.scan, view.symbol, view.zone, view.planState]);
  const [plan, setPlan] = useState<Row | null>(null);
  const [plans, setPlans] = useState<Row[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [note, setNote] = useState("Owner plan. Not an order.");
  const [index, setIndex] = useState("0");
  const [rejectReason, setRejectReason] = useState("");
  const [confirmApprove, setConfirmApprove] = useState(false);
  const [history, setHistory] = useState<{ events: Row[]; allowed: string[] | null }>({ events: [], allowed: null });
  const [checklist, setChecklist] = useState<Record<string, boolean | "">>(() => Object.fromEntries(PLAN_CHECKLIST.map((code) => [code, "" as const])));

  async function refreshList() {
    const result = await app.request<{ plans?: Row[]; counts_by_state?: Record<string, number> }>("/api/v1/plans", {
      query: filterState ? { state: filterState } : undefined,
    });
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setPlans(result.envelope.data.plans || []);
    setCounts(result.envelope.data.counts_by_state || {});
  }

  async function loadPlan(planId: string) {
    if (planId !== String(plan?.plan_id ?? "")) {
      // P10 review I-3: owner answers belong to one plan; never carry them to another.
      setChecklist(Object.fromEntries(PLAN_CHECKLIST.map((code) => [code, "" as const])));
      setIndex("0");
      setNote("Owner plan. Not an order.");
      setRejectReason("");
      setConfirmApprove(false);
    }
    const preview = await app.request<Row>(`/api/v1/plans/${planId}`);
    if (!preview.ok) {
      setMessage(preview.error.message);
      return;
    }
    setPlan(preview.envelope.data);
    setRationale(String(preview.envelope.data.rationale || ""));
    setMessage(null);
    await loadHistory(planId);
  }

  // Lifecycle and the transitions the backend allows (planning/states.py). The UI does not decide them.
  async function loadHistory(planId: string) {
    const result = await app.request<{ events?: Row[]; allowed_transitions?: string[] }>(`/api/v1/plans/${planId}/history`);
    if (result.ok) setHistory({ events: result.envelope.data.events ?? [], allowed: result.envelope.data.allowed_transitions ?? null });
    else setHistory({ events: [], allowed: null });
  }

  useEffect(() => {
    if (app.connection !== "connected") {
      setPlans([]);
      setPlan(null);
      return;
    }
    void refreshList();
    if (view.plan) void loadPlan(view.plan);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.connection, filterState, view.plan]);

  async function createPlan() {
    const result = await app.request<Row>("/api/v1/plans", {
      method: "POST",
      query: view.fixtures ? { include_fixtures: true } : undefined,
      body: { scan_key: scanKey, symbol, zone_id: zoneId, rationale: rationale || undefined },
    });
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    await loadPlan(String(result.envelope.data.plan_id));
    await refreshList();
  }

  async function approve() {
    const planId = String(plan?.plan_id || "");
    const unanswered = PLAN_CHECKLIST.filter((code) => typeof checklist[code] !== "boolean");
    if (unanswered.length) {
      setMessage("Every checklist item must be answered true or false before approval. Nothing was invented.");
      return;
    }
    const result = await app.request<Row>(`/api/v1/plans/${planId}/approve`, {
      method: "POST",
      body: {
        combination_index: Number(index),
        alert_note: note,
        checklist: Object.fromEntries(PLAN_CHECKLIST.map((code) => [code, checklist[code] === true])),
      },
    });
    if (!result.ok) setMessage(result.error.message);
    else {
      setPlan(result.envelope.data);
      setMessage("Approved in the research journal. No order was sent. authorises_order is false.");
      await loadHistory(planId);
      await refreshList();
    }
  }

  async function act(path: string, body?: Row, okMessage?: string) {
    const planId = String(plan?.plan_id || "");
    const result = await app.request<Row>(`/api/v1/plans/${planId}/${path}`, { method: "POST", body: body || {} });
    if (!result.ok) setMessage(result.error.message);
    else {
      setPlan(result.envelope.data);
      setMessage(okMessage || null);
      await loadHistory(planId);
      await refreshList();
    }
  }

  const combinations = Array.isArray(plan?.combinations) ? (plan?.combinations as Row[]) : [];
  const portfolioChecks = Array.isArray(plan?.portfolio_checks) ? (plan?.portfolio_checks as Row[]) : [];
  const capacity = (plan?.capacity || {}) as Row;
  const geometry = (plan?.geometry || {}) as Row;
  const manual = (plan?.manual_execution || {}) as Row;
  const prep = (manual.prep_fields || {}) as Row;
  const vsActual = (plan?.planned_versus_actual || null) as Row | null;
  const sourceQuality = String(plan?.source_quality || "");
  const unanswered = PLAN_CHECKLIST.filter((code) => typeof checklist[code] !== "boolean").length;
  // When the history route is unavailable every action stays visible; the backend still refuses invalid ones.
  const can = (target: string) => history.allowed === null || history.allowed.includes(target);
  const syncOk = plan?.journal_sync == null || ["IN_SYNC", "NO_JOURNAL_ENTRY"].includes(String(plan.journal_sync));

  return (
    <Page
      eyebrow="Trading"
      title="Trade Plans"
      description="A plan copies a stored candidate. Quantity stays empty until you select a printed buffer. Approval does not place an order. Execution is manual in Zerodha Kite outside this platform."
      meta={<span className="text-[11.5px] font-medium text-[var(--gtf-manual)]">Manual execution only. authorises_order is always false. A plan is not an order.</span>}
    >
      {view.rejected.length || view.ignored.length ? <Warning>Part of the address was ignored. The plan fields use only allowed query tokens.</Warning> : null}
      {sourceQuality === "FIXTURE" ? <Warning>FIXTURE source. Not certified market data. Not a live trade signal.</Warning> : null}
      {sourceQuality === "EXPLORATORY" ? <Warning>EXPLORATORY source. Not certified. P0 certified member-dates remain incomplete.</Warning> : null}

      <div className="grid grid-cols-3 gap-2 md:grid-cols-6" role="group" aria-label="Plans by state">
        {STATES.map(([code, label]) => (
          <button
            key={code}
            type="button"
            aria-pressed={filterState === code}
            onClick={() => setFilterState(filterState === code ? "" : code)}
            className={`panel px-3 py-2 text-left hover:border-line-strong ${filterState === code ? "border-[var(--gtf-accent)] bg-[var(--gtf-accent-bg)]" : ""}`}
          >
            <span className="eyebrow block">{label}</span>
            <span className="tabular text-[18px] font-semibold">{code in counts ? String(counts[code]) : "—"}</span>
          </button>
        ))}
      </div>
      <p className="text-[11.5px] text-muted" data-testid="plan-expiry-note">
        No automatic plan expiry runs. A plan shows EXPIRED only after the owner records EXPIRED on its journal entry. Journal CANCELLED and EXPIRED are mirrored onto the plan; the journal is the canonical record.
      </p>
      {message ? <Warning>{message}</Warning> : null}

      <div className="grid items-start gap-4 2xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="space-y-4">
          <Panel
            title="Plans"
            actions={
              <>
                <label className="flex items-center gap-1.5 text-[11.5px] text-muted">
                  Filter state
                  <select aria-label="Filter state" className="h-7 rounded-[4px] border border-line-strong px-1 text-[12px] text-ink" value={filterState} onChange={(event) => setFilterState(event.target.value)}>
                    <option value="">All</option>
                    {STATES.map(([code]) => (
                      <option key={code} value={code}>
                        {code}
                      </option>
                    ))}
                  </select>
                </label>
                <Button type="button" size="sm" onClick={() => void refreshList()}>
                  Refresh list
                </Button>
              </>
            }
            flush
          >
            {plans.length === 0 ? (
              <div className="p-3.5">
                <EmptyState title="No plans" reason="Create a draft from a stored scan candidate, or open one from Opportunities." />
              </div>
            ) : (
              <div className="scroll-thin overflow-auto">
                <table className="gtf-table w-full border-collapse text-[12px]">
                  <caption className="sr-only">Plans</caption>
                  <thead className="bg-surface-2">
                    <tr>
                      {["Symbol", "Plan state", "Canonical status", "Journal", "Created"].map((header) => (
                        <th key={header} scope="col" className="border-b border-line px-2.5 py-2 text-left">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {plans.map((row) => {
                      const id = String(row.plan_id);
                      const selected = plan?.plan_id === row.plan_id;
                      return (
                        <tr key={id} aria-selected={selected} className={selected ? "bg-[var(--gtf-selection)]" : undefined}>
                          <td className="border-b border-line px-2.5 py-1.5">
                            <button type="button" className="text-left" onClick={() => void loadPlan(id)}>
                              <span className="font-semibold text-[var(--gtf-accent)]">{String(row.symbol)}</span>
                              <span className="code block text-muted">
                                {id} · zone {String(row.zone_id)}
                              </span>
                            </button>
                          </td>
                          <td className="border-b border-line px-2.5">
                            <PlanState state={String(row.state)} />
                          </td>
                          <td className="border-b border-line px-2.5">
                            <StatusBadge code={String(row.candidate_status)} />
                          </td>
                          <td className="border-b border-line px-2.5 text-[11.5px]">
                            {row.entry_id != null ? (
                              <>
                                {String(row.journal_state ?? "unavailable")}
                                <SyncLabel value={row.journal_sync} />
                              </>
                            ) : (
                              <span className="text-muted">No entry</span>
                            )}
                          </td>
                          <td className="border-b border-line px-2.5 tabular text-muted">{formatDate(row.created_at) ?? "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
          <Panel title="New draft from a stored candidate" subtitle="Copies the candidate from the stored scan. The engine status is not changed.">
            <div className="grid grid-cols-2 gap-2">
              <TextInput label="Scan" value={scanKey} onChange={(event) => setScanKey(event.target.value)} />
              <TextInput label="Symbol" value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} />
              <TextInput label="Zone" value={zoneId} onChange={(event) => setZoneId(event.target.value)} />
              <TextInput id="plan-rationale" label="Rationale" value={rationale} onChange={(event) => setRationale(event.target.value)} />
            </div>
            <Button type="button" variant="primary" onClick={() => void createPlan()} disabled={!scanKey || !symbol || !zoneId}>
              Create draft
            </Button>
          </Panel>
        </div>

        <div className="space-y-4">
          {!plan ? (
            <Panel title="Plan detail">
              <EmptyState title="No plan selected" reason="Select a plan from the list, or create a draft from a stored candidate." />
            </Panel>
          ) : (
            <>
              <section className="panel">
                <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-3.5 py-3">
                  <div>
                    <p className="eyebrow">Plan · not an order</p>
                    <h2 className="text-[17px] font-semibold">
                      {String(plan.symbol)} <span className="code text-[12px] font-normal text-muted">{String(plan.plan_id)}</span>
                    </h2>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <PlanState state={String(plan.state || "")} />
                      <StatusBadge code={String(plan.candidate_status || "")} />
                      {sourceQuality === "FIXTURE" ? <ProvenanceBadge kind="FIXTURE" /> : sourceQuality === "EXPLORATORY" ? <ProvenanceBadge kind="EXPLORATORY" /> : null}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {plan.scan_key ? (
                      <Button type="button" size="sm" onClick={() => app.navigate("analysis", { symbol: String(plan.symbol), scan: String(plan.scan_key), fixtures: sourceQuality === "FIXTURE" ? "1" : null })}>
                        Open chart
                      </Button>
                    ) : null}
                    {plan.entry_id != null ? (
                      <Button type="button" size="sm" onClick={() => app.navigate("journal", { entry: String(plan.entry_id) })}>
                        Journal entry {String(plan.entry_id)}
                      </Button>
                    ) : null}
                  </div>
                </header>
                <div className="space-y-3 p-3.5">
                  <KeyValue
                    columns={2}
                    rows={[
                      ["Canonical status", <span className="code">{String(plan.candidate_status || "")}</span>],
                      ["Plan state", String(plan.state || "")],
                      ["Source quality", sourceQuality || "UNKNOWN"],
                      ["Quantity", plan.quantity == null ? <Unavailable /> : formatQuantity(plan.quantity) ?? String(plan.quantity)],
                      ["Monthly capacity", `${String(capacity.trades_triggered_this_month ?? "—")} / ${String(capacity.monthly_cap ?? "unavailable")}`],
                      ["Open positions", `${String(capacity.open_positions ?? "—")} / ${String(capacity.open_position_cap ?? "unavailable")}`],
                      ["Geometry", String(geometry.status || "UNAVAILABLE")],
                      ["Journal entry", plan.entry_id == null ? "none" : String(plan.entry_id)],
                      ["Journal state", plan.journal_state == null ? <Unavailable /> : String(plan.journal_state)],
                      ["Plan/journal sync", <SyncLabel value={plan.journal_sync} block={false} />],
                      ["Zone", <span className="code">{String(plan.zone_id || "")}</span>],
                      ["authorises_order", plan.authorises_order === true ? <span className="font-semibold text-[var(--gtf-fail)]">true (unexpected; treat as a defect)</span> : "false"],
                    ]}
                  />
                  {!syncOk ? (
                    <Warning>
                      Plan and journal are not confirmed consistent ({String(plan.journal_sync)}). The journal is the canonical record. Do not treat this plan state as current until the journal can be read.
                    </Warning>
                  ) : null}
                  {(plan.later_scan as Row | undefined)?.state ? <LaterScan later={plan.later_scan as Row} /> : null}
                  {plan.journal_zone_invalidated === true ? <Warning>The journal recorded ZONE_INVALIDATED for this entry. The plan is not drawn as live on the chart.</Warning> : null}
                  {plan.cancelled_by === "journal-sync" ? <p className="text-[12px]">Cancelled from the journal: {String(plan.cancel_reason || "")}.</p> : null}
                  {Array.isArray(geometry.reasons) && (geometry.reasons as string[]).length > 0 ? (
                    <ul className="list-disc space-y-0.5 pl-4 text-[12px] text-ink-2">
                      {(geometry.reasons as string[]).map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </section>

              <Panel title="Level combinations" subtitle="Printed by the risk module from the stored candidate. Choose a buffer index; nothing is recalculated here." flush>
                <div className="p-3.5">
                  {combinations.length === 0 && plan.state !== "APPROVED" ? (
                    <p className="text-[12px] text-muted">No buffer is selected. Quantity is unavailable until settings contain capital and a risk percent and the candidate has a structural target.</p>
                  ) : null}
                  {combinations.length ? (
                    <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
                      <table className="gtf-table w-full border-collapse text-[12px]">
                        <caption className="sr-only">Level combinations</caption>
                        <thead className="bg-surface-2">
                          <tr>
                            {["#", "Entry", "Stop", "Target", "Qty", "Risk / share", "Loss at stop", "R:R", "Status"].map((header, i) => (
                              <th key={header} scope="col" className={`border-b border-line px-2.5 py-2 ${i >= 1 && i <= 7 ? "text-right" : "text-left"}`}>
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {combinations.map((row, rowIndex) => (
                            <tr key={rowIndex} aria-selected={String(rowIndex) === index} className={String(rowIndex) === index ? "bg-[var(--gtf-selection)]" : undefined}>
                              <td className="border-b border-line px-2.5 py-1.5">
                                <label className="flex items-center gap-1.5">
                                  <input type="radio" name="buffer" checked={String(rowIndex) === index} onChange={() => setIndex(String(rowIndex))} aria-label={`Use combination ${rowIndex}`} />
                                  {rowIndex}
                                </label>
                              </td>
                              <td className="num border-b border-line px-2.5">{formatPrice(row.entry) ?? String(row.entry)}</td>
                              <td className="num border-b border-line px-2.5">{formatPrice(row.stop) ?? String(row.stop)}</td>
                              <td className="num border-b border-line px-2.5">{formatPrice(row.target) ?? String(row.target)}</td>
                              <td className="num border-b border-line px-2.5">{formatQuantity(row.quantity) ?? String(row.quantity)}</td>
                              <td className="num border-b border-line px-2.5">{formatPrice(row.risk_per_share) ?? String(row.risk_per_share)}</td>
                              <td className="num border-b border-line px-2.5">{formatInr(row.loss_if_stopped) ?? String(row.loss_if_stopped)}</td>
                              <td className="num border-b border-line px-2.5">{text(row.rr) ?? "—"}</td>
                              <td className="border-b border-line px-2.5">
                                <StatusBadge code={String(row.status)} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                  {portfolioChecks.length ? (
                    <ul className="mt-3 space-y-1 text-[12px]">
                      {portfolioChecks.map((check) => (
                        <li key={String(check.code)} className="flex flex-wrap items-baseline gap-2">
                          <span className="code">{String(check.code)}</span>
                          <StatusBadge code={String(check.outcome)} />
                          <span className="text-muted">{String(check.reason)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </Panel>

              {plan.state === "DRAFT" || plan.state === "AWAITING_OWNER" || plan.state === "APPROVED" ? (
                <Panel title="Manual execution preparation" subtitle={String(manual.instruction || "Execution takes place manually outside the platform.")}>
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    <Prep label="Symbol" value={String(prep.symbol || plan.symbol)} />
                    <Prep label="Quantity" value={prep.quantity == null ? "awaiting buffer" : formatQuantity(prep.quantity) ?? String(prep.quantity)} />
                    <Prep label="Entry" value={formatPrice(prep.proposed_entry) ?? "—"} />
                    <Prep label="Stop" value={formatPrice(prep.stop_loss) ?? "—"} />
                    <Prep label="Target" value={formatPrice(prep.target) ?? "—"} />
                    <Prep label="Zone" value={String(prep.zone_id || plan.zone_id)} />
                    <Prep label="Qualification" value={String(prep.canonical_qualification || plan.candidate_status)} wide />
                  </div>
                </Panel>
              ) : null}

              {vsActual ? (
                <Panel title={`Planned versus actual (${String(vsActual.state)})`} subtitle={String(vsActual.note || "")}>
                  <PlannedActual planned={vsActual.planned} actual={vsActual.actual} />
                </Panel>
              ) : null}

              <Panel title="Plan lifecycle" subtitle="Recorded state changes from /api/v1/plans/{id}/history.">
                {history.events.length === 0 ? <p className="text-[12px] text-muted">No lifecycle event returned.</p> : null}
                <ol className="space-y-1.5 border-l-2 border-line pl-3 text-[12px]">
                  {history.events.map((event, i) => (
                    <li key={String(event.event_id ?? i)}>
                      <span className="tabular text-muted">{formatDate(event.at) ?? "—"}</span>{" "}
                      <span className="font-medium">{String(event.action ?? "")}</span>{" "}
                      <span className="text-muted">
                        {String(event.from_state ?? "—")} → {String(event.to_state ?? "—")} · {String(event.actor ?? "")}
                      </span>
                    </li>
                  ))}
                </ol>
              </Panel>

              <Panel title="Owner review" subtitle="Each checklist item must be answered. Unanswered items block approval. UI state alone cannot approve.">
                <div className="grid gap-x-4 gap-y-1.5 md:grid-cols-2">
                  {PLAN_CHECKLIST.map((code) => (
                    <label key={code} className="flex items-center justify-between gap-2 border-b border-line py-1">
                      <span className="code">{code}</span>
                      <select
                        aria-label={code}
                        className="h-7 rounded-[4px] border border-line-strong px-1 text-[12px]"
                        value={checklist[code] === true ? "true" : checklist[code] === false ? "false" : ""}
                        onChange={(event) => {
                          const raw = event.target.value;
                          setChecklist((current) => ({ ...current, [code]: raw === "true" ? true : raw === "false" ? false : "" }));
                        }}
                      >
                        <option value="">Unanswered</option>
                        <option value="true">True</option>
                        <option value="false">False</option>
                      </select>
                    </label>
                  ))}
                </div>
                <p className="text-[11.5px] text-muted">{unanswered ? `${unanswered} of ${PLAN_CHECKLIST.length} items unanswered.` : "All checklist items answered."}</p>
                {history.allowed !== null ? (
                  <p className="text-[11.5px] text-muted" data-testid="plan-allowed-transitions">
                    Transitions the backend allows from {String(plan.state)}: {history.allowed.length ? history.allowed.join(", ") : "none (terminal state)"}.
                  </p>
                ) : null}
                <div className="grid gap-2 md:grid-cols-3">
                  <TextInput label="Buffer index" value={index} onChange={(event) => setIndex(event.target.value)} />
                  <TextInput label="Note" value={note} onChange={(event) => setNote(event.target.value)} />
                  <TextInput label="Reject / cancel reason" value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} />
                </div>
                <TextInput id="plan-rationale-edit" label="Plan rationale" value={rationale} onChange={(event) => setRationale(event.target.value)} />
                <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
                  {can("AWAITING_OWNER") ? (
                  <Button type="button" onClick={() => void act("submit", { note }, "Submitted for owner review.")}>
                    Submit for review
                  </Button>
                  ) : null}
                  {can("APPROVED") ? (
                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => {
                      if (unanswered) {
                        setMessage("Every checklist item must be answered true or false before approval. Nothing was invented.");
                        return;
                      }
                      setConfirmApprove(true);
                    }}
                  >
                    Approve plan
                  </Button>
                  ) : null}
                  {can("REJECTED") ? (
                  <Button
                    type="button"
                    variant="danger"
                    onClick={() => {
                      if (!rejectReason.trim()) {
                        setMessage("Reject requires an explicit owner reason. Nothing was invented.");
                        return;
                      }
                      void act("reject", { reason: rejectReason.trim() }, "Plan rejected.");
                    }}
                  >
                    Reject
                  </Button>
                  ) : null}
                  {plan.state === "APPROVED" && plan.entry_id != null ? (
                    <p className="text-[12px] text-muted" data-testid="cancel-in-journal">
                      This approved plan has journal entry {String(plan.entry_id)}. Cancel it in the Journal (record CANCELLED); the plan mirrors the journal (ED-3).
                    </p>
                  ) : can("CANCELLED") ? (
                    <Button
                      type="button"
                      onClick={() => {
                        if (!rejectReason.trim()) {
                          setMessage("Cancel requires an explicit owner reason. Nothing was invented.");
                          return;
                        }
                        void act("cancel", { reason: rejectReason.trim() }, "Plan cancelled.");
                      }}
                    >
                      Cancel
                    </Button>
                  ) : null}
                  {can("DRAFT") ? (
                  <Button type="button" variant="ghost" onClick={() => void act("reopen", {}, "Returned to DRAFT.")}>
                    Reopen draft
                  </Button>
                  ) : null}
                  <Button type="button" variant="ghost" onClick={() => void act("rationale", { rationale }, "Rationale saved.")}>
                    Save rationale
                  </Button>
                </div>
              </Panel>
            </>
          )}
        </div>
      </div>
      {confirmApprove && plan ? (
        <Dialog
          title={`Approve ${String(plan.symbol)} plan`}
          body={`Approval records the plan in the research journal with buffer index ${index}. No order is sent and authorises_order stays false. You place any order yourself in Kite.`}
          confirm="Approve plan"
          onClose={() => setConfirmApprove(false)}
          onConfirm={() => {
            setConfirmApprove(false);
            void approve();
          }}
        />
      ) : null}
    </Page>
  );
}

function PlanState({ state }: { state: string }) {
  const tone =
    state === "APPROVED"
      ? "border-[var(--gtf-info)]/50 text-[var(--gtf-info)]"
      : state === "REJECTED" || state === "CANCELLED" || state === "EXPIRED"
        ? "border-line-strong text-muted"
        : "border-[var(--gtf-manual)]/50 text-[var(--gtf-manual)]";
  return <span className={`inline-flex rounded-[3px] border px-1.5 py-[1px] text-[11px] font-semibold ${tone}`}>{state}</span>;
}

function SyncLabel({ value, block = true }: { value: unknown; block?: boolean }) {
  const sync = value == null ? "unknown" : String(value);
  const ok = sync === "IN_SYNC" || sync === "NO_JOURNAL_ENTRY";
  return (
    <span className={`${block ? "block" : ""} text-[11px] ${ok ? "text-muted" : "font-semibold text-[var(--gtf-manual)]"}`}>
      {ok ? "" : "! "}({sync})
    </span>
  );
}

function Prep(props: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={props.wide ? "col-span-2" : ""}>
      <p className="text-[10.5px] text-muted">{props.label}</p>
      <p className="tabular break-words text-[13px] font-medium">{props.value}</p>
    </div>
  );
}

function PlannedActual(props: { planned: unknown; actual: unknown }) {
  const planned = (props.planned || {}) as Row;
  const actual = (props.actual || {}) as Row;
  const keys = Array.from(new Set([...Object.keys(planned), ...Object.keys(actual)]));
  if (!keys.length) return <p className="text-[12px] text-muted">No comparable fields were returned.</p>;
  return (
    <KeyValue
      rows={keys.map((key) => [key, <span className="tabular">{fmt(planned[key])} → {fmt(actual[key])}</span>] as [string, ReactNode])}
    />
  );
}

function fmt(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function LaterScan(props: { later: Row }) {
  const later = props.later;
  const state = String(later.state);
  const differences = Array.isArray(later.differences) ? (later.differences as Row[]) : [];
  if (state === "NO_LATER_SCAN") return <p className="text-[12px] text-muted" data-testid="later-scan">No later stored scan covers this symbol (FR-5.9).</p>;
  if (state === "UNCHANGED") {
    return <p className="text-[12px] text-muted" data-testid="later-scan">Later scan {String(later.scan_key)} holds the same candidate values.</p>;
  }
  return (
    <div data-testid="later-scan" data-state={state}>
      <Warning>
        {state === "UNAVAILABLE" ? String(later.reason || "Later-scan comparison unavailable.") : `Later scan ${String(later.scan_key)} (as of ${String(later.as_of)}): ${String(later.reason || state)}`}
        {differences.map((item) => (
          <span key={String(item.field)} className="block">
            {String(item.field)}: plan {JSON.stringify(item.plan)} · later scan {JSON.stringify(item.later_scan)}
          </span>
        ))}
      </Warning>
    </div>
  );
}
