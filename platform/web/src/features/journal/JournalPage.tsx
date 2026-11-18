import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, Dialog, EmptyState, KeyValue, Page, Panel, SelectInput, TextInput, Unavailable } from "../../design/components";
import { formatDate, formatInr, formatPaise, formatPrice, formatQuantity, text, toNumber } from "../../design/format";
import { readViewQuery } from "../../navigation/query";
import { useAppState } from "../../state/store";
import { Warning } from "../shared/ui";

function newKey(): string {
  return crypto.randomUUID();
}

function unavailable(value: unknown): string {
  if (value === null || value === undefined || value === "") return "unavailable";
  return String(value);
}

type Pending = { title: string; body: string; confirm: string; run: () => void } | null;

/**
 * P10-8 Trading Journal. The research journal is the canonical execution record. This screen
 * records owner-typed facts only; it does not retrieve fills from Zerodha and places no order.
 */
export function JournalPage() {
  const app = useAppState();
  const view = useMemo(() => readViewQuery(app.queryString), [app.queryString]);
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [total, setTotal] = useState(0);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [performance, setPerformance] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [entryId, setEntryId] = useState(view.entry);
  const [orderRef, setOrderRef] = useState("");
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [printKey, setPrintKey] = useState("");
  const [printSide, setPrintSide] = useState("ENTRY");
  const [noteBody, setNoteBody] = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [outcomeClass, setOutcomeClass] = useState("NOT_CLASSIFIED");
  const [mistakeCategory, setMistakeCategory] = useState("NONE");
  const [setupLabel, setSetupLabel] = useState("");
  const [chargePaise, setChargePaise] = useState("");
  const [exportText, setExportText] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending>(null);

  function queryPath(path: string): string {
    const params = new URLSearchParams();
    if (symbol.trim()) params.set("symbol", symbol.trim());
    if (stateFilter) params.set("state", stateFilter);
    if (reviewFilter) params.set("review_status", reviewFilter);
    const qs = params.toString();
    return qs ? `${path}?${qs}` : path;
  }

  async function loadList() {
    setLoading(true);
    const result = await app.request<{ entries?: Array<Record<string, unknown>>; total?: number }>(queryPath("/api/v1/journal"));
    setLoading(false);
    if (!result.ok) {
      app.reportFailure(result);
      setMessage(result.error.message);
      setRows([]);
      setTotal(0);
      return;
    }
    setRows(result.envelope.data.entries || []);
    setTotal(Number(result.envelope.data.total || 0));
    setMessage(null);
  }

  async function loadDetail(id: string) {
    if (!id.trim()) {
      setDetail(null);
      return;
    }
    const result = await app.request<Record<string, unknown>>(`/api/v1/journal/${encodeURIComponent(id.trim())}`);
    if (!result.ok) {
      app.reportFailure(result);
      setMessage(result.error.message);
      setDetail(null);
      return;
    }
    setDetail(result.envelope.data);
  }

  async function loadPerformance() {
    const result = await app.request<Record<string, unknown>>(queryPath("/api/v1/journal/performance"));
    if (!result.ok) {
      app.reportFailure(result);
      setMessage(result.error.message);
      setPerformance(null);
      return;
    }
    setPerformance(result.envelope.data);
  }

  function refreshAll() {
    void loadList();
    void loadDetail(entryId);
    void loadPerformance();
  }

  useEffect(() => {
    setEntryId(view.entry);
  }, [view.entry]);

  useEffect(() => {
    if (app.connection !== "connected") {
      setRows([]);
      setDetail(null);
      setPerformance(null);
      setMessage(null);
      return;
    }
    void loadList();
    void loadPerformance();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.connection]);

  useEffect(() => {
    if (app.connection !== "connected") return;
    if (entryId.trim()) void loadDetail(entryId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.connection, entryId]);

  const totals = (performance?.totals || null) as Record<string, unknown> | null;
  const comparison = (detail?.planned_versus_actual || null) as Record<string, unknown> | null;
  const review = (detail?.review || null) as Record<string, unknown> | null;
  const connected = app.connection === "connected";
  const filtered = Boolean(symbol || stateFilter || reviewFilter);
  const hasEntry = Boolean(entryId.trim());

  function post(path: string, body: Record<string, unknown>, ok: string | ((data: Record<string, unknown>) => string)) {
    void app
      .request<Record<string, unknown>>(`/api/v1/journal/${encodeURIComponent(entryId.trim())}/${path}`, { method: "POST", idempotencyKey: newKey(), body })
      .then((result) => {
        if (!result.ok) app.reportFailure(result);
        setMessage(result.ok ? (typeof ok === "function" ? ok(result.envelope.data) : ok) : result.error.message);
        refreshAll();
      });
  }

  return (
    <Page
      eyebrow="Trading"
      title="Trading Journal"
      description="Canonical research-journal records of plans and owner-typed fills. This screen does not retrieve fills from Zerodha and does not place orders. Performance figures are JOURNAL_DESCRIPTIVE, not certified strategy results."
      actions={
        connected ? (
          <Button
            type="button"
            onClick={() =>
              void app.request<Record<string, unknown>>(queryPath("/api/v1/journal/export")).then((result) => {
                if (!result.ok) {
                  app.reportFailure(result);
                  setMessage(result.error.message);
                  setExportText(null);
                  return;
                }
                setExportText(JSON.stringify(result.envelope.data, null, 2));
                setMessage(`Export ready (${String((result.envelope.data as { total?: unknown }).total ?? 0)} rows). Attachments are referenced, not embedded.`);
              })
            }
          >
            Export filtered journal
          </Button>
        ) : null
      }
    >
      {message ? <Warning>{message}</Warning> : null}
      {!connected ? <EmptyState title="Journal unavailable" reason="The API session is not authenticated. Rows from a previous session are not shown." /> : null}

      {connected && totals ? (
        <section className="panel px-3.5 py-3" data-testid="journal-performance">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-[13px] font-semibold">Performance summary ({String(performance?.evidence_class || "JOURNAL_DESCRIPTIVE")})</h2>
            <p className="text-[11.5px] text-muted">
              Descriptive record of {unavailable(totals.recorded_trades)} recorded trades. Not certified strategy performance. Small samples say little about the method.
            </p>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-x-5 gap-y-2 md:grid-cols-6 2xl:grid-cols-10">
            <Stat label="Recorded" value={text(totals.recorded_trades)} />
            <Stat label="Open" value={text(totals.open_trades)} />
            <Stat label="Closed" value={text(totals.closed_trades)} />
            <Stat label="Wins" value={text(totals.wins)} />
            <Stat label="Losses" value={text(totals.losses)} />
            <Stat label="Gross realised" value={formatInr(totals.gross_realised_pnl) ?? text(totals.gross_realised_pnl)} />
            <Stat label={`Net realised (${unavailable(totals.net_state)})`} value={formatInr(totals.net_realised_pnl) ?? text(totals.net_realised_pnl)} />
            <Stat label="Known charges" value={formatPaise(totals.known_charges_paise)} />
            <Stat label="Reviewed" value={text(totals.reviewed)} />
            <Stat label="Unreviewed" value={text(totals.unreviewed)} />
          </div>
        </section>
      ) : null}

      {connected ? (
        <section className="panel flex flex-wrap items-end gap-3 px-3.5 py-3" data-testid="journal-filters">
          <p className="sr-only">Search and filters</p>
          <TextInput label="Symbol" value={symbol} onChange={(event) => setSymbol(event.target.value)} className="w-36" />
          <SelectInput label="Lifecycle state" value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}>
            <option value="">All</option>
            {["PLANNED", "OPEN", "CLOSED", "CANCELLED", "EXPIRED"].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </SelectInput>
          <SelectInput label="Review status" value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)}>
            <option value="">All</option>
            <option value="NOT_REVIEWED">NOT_REVIEWED</option>
            <option value="REVIEWED">REVIEWED</option>
          </SelectInput>
          <Button type="button" variant="primary" onClick={() => { void loadList(); void loadPerformance(); }}>
            Apply filters
          </Button>
          <Button
            type="button"
            onClick={() => {
              setSymbol("");
              setStateFilter("");
              setReviewFilter("");
              void loadList();
              void loadPerformance();
            }}
          >
            Clear filters
          </Button>
          <p className="ml-auto text-[12px] text-muted" data-testid="journal-result-count">
            Showing {rows.length} of {total} stored rows.
          </p>
        </section>
      ) : null}

      {connected ? (
        <div className="grid items-start gap-4 2xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
          <Panel title="Entries" subtitle="Select an entry to open its record." flush>
            {loading ? (
              <div className="p-3.5">
                <EmptyState title="Loading journal" reason="Reading canonical research-journal rows." />
              </div>
            ) : null}
            {!loading && rows.length === 0 ? (
              <div className="p-3.5">
                <EmptyState
                  title={total === 0 && !filtered ? "No journal rows" : "No search results"}
                  reason={total === 0 && !filtered ? "An approved plan creates the first row." : "Filters matched no stored journal rows. This is not an error."}
                />
              </div>
            ) : null}
            {rows.length ? (
              <div className="scroll-thin overflow-auto">
                <table className="gtf-table w-full border-collapse text-[12px]">
                  <caption className="sr-only">Journal entries</caption>
                  <thead className="bg-surface-2">
                    <tr>
                      {["Entry", "Symbol", "State", "Entry / stop / target", "Qty", "Open", "Avg entry", "Charges", "Review"].map((header, index) => (
                        <th key={header} scope="col" className={`border-b border-line px-2.5 py-2 ${index >= 3 && index <= 6 ? "text-right" : "text-left"}`}>
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => {
                      const book = (row.book || {}) as Record<string, unknown>;
                      const id = String(row.entry_id);
                      const selected = entryId === id;
                      return (
                        <tr key={id} data-testid={`journal-row-${id}`} aria-selected={selected} className={selected ? "bg-[var(--gtf-selection)]" : undefined}>
                          <td className="border-b border-line px-2.5 py-1.5">
                            <button
                              type="button"
                              className="font-medium text-[var(--gtf-accent)] underline-offset-2 hover:underline"
                              onClick={() => {
                                setEntryId(id);
                                app.navigate("journal", { entry: id });
                              }}
                            >
                              Entry {id}
                            </button>
                          </td>
                          <td className="border-b border-line px-2.5">
                            <span className="font-semibold">{String(row.symbol)}</span>
                            <span className="code block text-muted">zone {String(row.zone_id)}</span>
                          </td>
                          <td className="border-b border-line px-2.5">
                            <span className="sr-only">State </span>
                            {String(row.state)}
                          </td>
                          <td className="num border-b border-line px-2.5">
                            {num(row.planned_entry)} / {num(row.planned_stop)} / {num(row.planned_target)}
                          </td>
                          <td className="num border-b border-line px-2.5">{qty(row.quantity)}</td>
                          <td className="num border-b border-line px-2.5">{qty(book.open_quantity)}</td>
                          <td className="num border-b border-line px-2.5">{num(book.average_entry_price)}</td>
                          <td className="border-b border-line px-2.5">
                            <span className="sr-only">Charges </span>
                            {String(row.charges_state || "ABSENT")}
                          </td>
                          <td className="border-b border-line px-2.5">
                            <span className="sr-only">Review </span>
                            {String((row.review as { review_status?: unknown } | undefined)?.review_status || "NOT_REVIEWED")}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </Panel>

          <div className="space-y-4">
            {detail ? (
              <section className="panel" data-testid="journal-detail">
                <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3.5 py-2.5">
                  <h2 className="text-[13px] font-semibold">Trade detail {String((detail.entry as { entry_id?: unknown } | undefined)?.entry_id ?? entryId)}</h2>
                  <span className="text-[11.5px] text-muted">
                    Lifecycle {unavailable(detail.state)} · Charges {unavailable(detail.charges_state)}
                  </span>
                </header>
                <div className="space-y-4 p-3.5">
                  <EntrySummary entry={(detail.entry || {}) as Record<string, unknown>} />
                  <KeyValue
                    columns={2}
                    rows={[
                      ["Review", unavailable(review?.review_status)],
                      ["Outcome class", unavailable(review?.outcome_class)],
                      ["Mistake category", unavailable(review?.mistake_category)],
                      ["Setup label", unavailable(review?.setup_label)],
                    ]}
                  />
                  {comparison ? (
                    <div data-testid="journal-planned-versus-actual">
                      <SubHeading>Planned versus actual ({unavailable(comparison.state)})</SubHeading>
                      <Comparison comparison={comparison} />
                    </div>
                  ) : null}
                  <div>
                    <SubHeading>Executions</SubHeading>
                    <Records rows={detail.executions} empty="No executions recorded. No fill is implied." />
                  </div>
                  <div>
                    <SubHeading>Events</SubHeading>
                    <Records rows={detail.events} empty="No events recorded." />
                  </div>
                  <div>
                    <SubHeading>Notes</SubHeading>
                    <Records rows={detail.notes} empty="No notes." />
                  </div>
                  <div>
                    <SubHeading>Attachments</SubHeading>
                    <Attachments entryId={entryId} rows={detail.attachments} />
                  </div>
                </div>
              </section>
            ) : (
              <Panel title="Trade detail">
                <EmptyState title="No entry selected" reason="Choose an entry from the list or type its id below." />
              </Panel>
            )}

            <section className="panel space-y-3 px-3.5 py-3" data-testid="journal-actions">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h2 className="text-[13px] font-semibold">Record owner facts</h2>
                  <p className="text-[11.5px] text-muted">Each action appends to the journal. Execution facts are never overwritten. Nothing is sent to a broker.</p>
                </div>
                <TextInput label="Entry id" value={entryId} onChange={(event) => setEntryId(event.target.value)} className="w-28" />
              </div>
              <ActionGroup title="Order submission and prints" open>
                <div className="flex flex-wrap items-end gap-2">
                  <TextInput label="Kite order reference" value={orderRef} onChange={(event) => setOrderRef(event.target.value)} className="w-48" />
                  <Button
                    type="button"
                    disabled={!hasEntry}
                    onClick={() => post("order", { submitted_at: new Date().toISOString(), order_ref: orderRef, note: "Owner submitted in Kite" }, "Submission recorded. No order was sent.")}
                  >
                    Record submission
                  </Button>
                </div>
                <div className="flex flex-wrap items-end gap-2">
                  <TextInput label="Print quantity" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="w-28" inputMode="numeric" />
                  <TextInput label="Print price" value={price} onChange={(event) => setPrice(event.target.value)} className="w-28" inputMode="decimal" />
                  <TextInput label="Print key" value={printKey} onChange={(event) => setPrintKey(event.target.value)} className="w-32" />
                  <SelectInput label="Print side" value={printSide} onChange={(event) => setPrintSide(event.target.value)}>
                    <option value="ENTRY">ENTRY</option>
                    <option value="EXIT">EXIT</option>
                  </SelectInput>
                  <Button
                    type="button"
                    disabled={!hasEntry}
                    onClick={() => {
                      const amount = Number(quantity);
                      const key = printKey.trim() || `print-${Date.now()}`;
                      if (!Number.isInteger(amount) || amount <= 0) {
                        setMessage("Print quantity must be a positive whole number of shares.");
                        return;
                      }
                      const printPrice = Number(price);
                      if (!price.trim() || !Number.isFinite(printPrice) || printPrice <= 0) {
                        setMessage("Print price must be a positive number. Nothing was recorded.");
                        return;
                      }
                      post(
                        "executions",
                        { side: printSide, quantity: amount, price: Number(price), at: new Date().toISOString(), print_key: key },
                        "Print recorded. This app did not place the order.",
                      );
                    }}
                  >
                    Record print
                  </Button>
                </div>
              </ActionGroup>
              <ActionGroup title="Close or cancel">
                <div className="flex flex-wrap items-end gap-2">
                  <Button
                    type="button"
                    disabled={!hasEntry}
                    onClick={() => {
                      // P10 review I-1: a blank price must not become 0 in the canonical journal.
                      const closePrice = Number(price);
                      if (!price.trim() || !Number.isFinite(closePrice) || closePrice <= 0) {
                        setMessage("Record close needs the exit price in the Print price field. Nothing was recorded.");
                        return;
                      }
                      setPending({
                        title: `Record a manual close for entry ${entryId}`,
                        body: `Records CLOSED_MANUAL at price ${price}. The monthly allowance is not restored. Nothing is sent to Kite.`,
                        confirm: "Record close",
                        run: () =>
                          post(
                            "events",
                            { kind: "CLOSED_MANUAL", at: new Date().toISOString(), price: Number(price), note: "Owner closed in Kite. Recorded here only." },
                            "Close recorded. The monthly allowance was not restored.",
                          ),
                      });
                    }}
                  >
                    Record close event
                  </Button>
                  <TextInput label="Cancel reason" value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} className="w-56" />
                  <Button
                    type="button"
                    variant="danger"
                    disabled={!hasEntry}
                    onClick={() => {
                      if (!cancelReason.trim()) {
                        setMessage("Cancel requires an explicit owner reason. Nothing was invented.");
                        return;
                      }
                      setPending({
                        title: `Record CANCELLED for entry ${entryId}`,
                        body: "The journal decides whether CANCELLED is allowed. A linked plan mirrors the journal. No order is touched.",
                        confirm: "Record CANCELLED",
                        // P4-IR-04: the journal is canonical; the linked platform plan mirrors the result.
                        run: () =>
                          post("events", { kind: "CANCELLED", at: new Date().toISOString(), note: cancelReason.trim() }, (data) => {
                            const sync = (data as { plan_sync?: { status?: string; synced?: string[] } }).plan_sync;
                            return `CANCELLED recorded in the journal. Linked plan sync: ${sync?.status ?? "unknown"}${sync?.synced?.length ? ` (${sync.synced.join(", ")})` : ""}. No order was touched.`;
                          }),
                      });
                    }}
                  >
                    Record CANCELLED
                  </Button>
                </div>
              </ActionGroup>
              <ActionGroup title="Charges">
                <div className="flex flex-wrap items-end gap-2">
                  <TextInput label="Charge amount (paise)" value={chargePaise} onChange={(event) => setChargePaise(event.target.value)} className="w-40" inputMode="numeric" />
                  <Button
                    type="button"
                    disabled={!hasEntry}
                    onClick={() => {
                      const amount = Number(chargePaise);
                      if (!Number.isInteger(amount) || amount < 0) {
                        setMessage("Charge amount must be a non-negative whole number of paise.");
                        return;
                      }
                      post(
                        "charges",
                        {
                          mode: "ACTUAL",
                          at: new Date().toISOString(),
                          source: "OWNER_ENTERED",
                          lines: [{ charge_key: `owner-${Date.now()}`, component: "OTHER", side: "BUY", amount_paise: amount, basis: "Owner-entered actual charge. Not a broker tariff." }],
                        },
                        "Charge recorded. Missing charges stay ABSENT elsewhere.",
                      );
                    }}
                  >
                    Record actual charge
                  </Button>
                  <p className="text-[11.5px] text-muted">{toNumber(chargePaise) !== null ? `= ${formatPaise(chargePaise)}` : "Whole paise. No tariff is built in (B12)."}</p>
                </div>
              </ActionGroup>
              <ActionGroup title="Review and mistakes">
                <TextInput label="Review note" value={noteBody} onChange={(event) => setNoteBody(event.target.value)} />
                <div className="flex flex-wrap items-end gap-2">
                  <Button
                    type="button"
                    disabled={!hasEntry}
                    onClick={() => post("notes", { note_key: `note-${Date.now()}`, at: new Date().toISOString(), kind: "POST_TRADE_REVIEW", body: noteBody }, "Note appended. Execution facts were not changed.")}
                  >
                    Add review note
                  </Button>
                  <SelectInput label="Outcome class" value={outcomeClass} onChange={(event) => setOutcomeClass(event.target.value)}>
                    {["NOT_CLASSIFIED", "DISCIPLINE_LOSS", "PROBABILITY_LOSS", "DISCIPLINE_WIN", "LUCKY_WIN"].map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </SelectInput>
                  <SelectInput label="Mistake category" value={mistakeCategory} onChange={(event) => setMistakeCategory(event.target.value)}>
                    {["NONE", "RULE_VIOLATION", "EXECUTION", "PLANNING", "RISK_MANAGEMENT", "DATA_LIMITATION", "PSYCHOLOGY"].map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </SelectInput>
                  <TextInput label="Setup label" value={setupLabel} onChange={(event) => setSetupLabel(event.target.value)} className="w-36" />
                  <Button
                    type="button"
                    disabled={!hasEntry}
                    onClick={() =>
                      post(
                        "reviews",
                        {
                          review_key: `review-${Date.now()}`,
                          at: new Date().toISOString(),
                          review_status: "REVIEWED",
                          outcome_class: outcomeClass,
                          mistake_category: mistakeCategory,
                          setup_label: setupLabel.trim() || undefined,
                          note: noteBody || "Owner review classification.",
                        },
                        "Review classification appended.",
                      )
                    }
                  >
                    Mark reviewed
                  </Button>
                </div>
              </ActionGroup>
              <ActionGroup title="Screenshot attachment">
                <label className="block text-[12px]" data-testid="journal-attachment-upload">
                  Screenshot attachment (png/jpeg/webp/gif)
                  <input
                    aria-label="Screenshot attachment"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    className="mt-1 block text-[12px]"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.target.value = "";
                      if (!file) return;
                      if (!entryId.trim()) {
                        setMessage("Select a journal entry before attaching a screenshot.");
                        return;
                      }
                      const reader = new FileReader();
                      reader.onload = () => {
                        const raw = String(reader.result || "");
                        const marker = "base64,";
                        const idx = raw.indexOf(marker);
                        if (idx < 0) {
                          setMessage("Attachment could not be read as base64.");
                          return;
                        }
                        post(
                          "attachments",
                          {
                            attachment_id: `shot-${Date.now()}`,
                            at: new Date().toISOString(),
                            filename: file.name.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 180) || "chart.png",
                            content_type: file.type,
                            content_base64: raw.slice(idx + marker.length),
                            note: "Owner-attached chart screenshot.",
                          },
                          "Screenshot attached. Execution facts were not changed.",
                        );
                      };
                      reader.onerror = () => setMessage("Attachment file could not be read.");
                      reader.readAsDataURL(file);
                    }}
                  />
                </label>
              </ActionGroup>
            </section>
            {exportText ? (
              <Panel title="Export">
                <pre className="scroll-thin code max-h-64 overflow-auto whitespace-pre-wrap" data-testid="journal-export">
                  {exportText}
                </pre>
              </Panel>
            ) : null}
          </div>
        </div>
      ) : null}
      {pending ? (
        <Dialog
          title={pending.title}
          body={pending.body}
          confirm={pending.confirm}
          onClose={() => setPending(null)}
          onConfirm={() => {
            const run = pending.run;
            setPending(null);
            run();
          }}
        />
      ) : null}
    </Page>
  );
}

function num(value: unknown): ReactNode {
  return formatPrice(value) ?? <span className="text-muted">—</span>;
}

function qty(value: unknown): ReactNode {
  return formatQuantity(value) ?? <span className="text-muted">—</span>;
}

function Stat(props: { label: string; value: string | null }) {
  return (
    <div className="min-w-0">
      <p className="text-[10.5px] text-muted">{props.label}</p>
      <p className="tabular text-[14px] font-semibold">{props.value ?? <span className="text-[12px] font-normal text-muted">unavailable</span>}</p>
    </div>
  );
}

function SubHeading(props: { children: ReactNode }) {
  return <h3 className="eyebrow mb-1.5">{props.children}</h3>;
}

function ActionGroup(props: { title: string; open?: boolean; children: ReactNode }) {
  return (
    <details className="rounded-[4px] border border-line" open={props.open}>
      <summary className="cursor-pointer px-3 py-2 text-[12.5px] font-medium">{props.title}</summary>
      <div className="space-y-2 border-t border-line px-3 py-2.5">{props.children}</div>
    </details>
  );
}

function EntrySummary(props: { entry: Record<string, unknown> }) {
  const entry = props.entry;
  if (!Object.keys(entry).length) return null;
  return (
    <KeyValue
      columns={2}
      rows={[
        ["Symbol", text(entry.symbol) ?? <Unavailable />],
        ["Zone", <span className="code">{text(entry.zone_id) ?? "unavailable"}</span>],
        ["Planned entry", num(entry.planned_entry)],
        ["Planned stop", num(entry.planned_stop)],
        ["Planned target", num(entry.planned_target)],
        ["Planned quantity", qty(entry.quantity)],
      ]}
    />
  );
}

const PREFERRED = ["at", "kind", "side", "quantity", "price", "print_key", "order_ref", "body", "note", "filename", "content_type", "attachment_id"];

/** Renders an array of journal records as a table. Values are shown as stored; nested objects as compact text. */
function Records(props: { rows: unknown; empty: string }) {
  const rows = Array.isArray(props.rows) ? (props.rows as Array<Record<string, unknown>>).filter((row) => row && typeof row === "object") : [];
  if (rows.length === 0) return <p className="text-[12px] text-muted">{props.empty}</p>;
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  const ordered = [...PREFERRED.filter((key) => keys.includes(key)), ...keys.filter((key) => !PREFERRED.includes(key))].slice(0, 7);
  return (
    <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
      <table className="gtf-table w-full border-collapse text-[11.5px]">
        <thead className="bg-surface-2">
          <tr>
            {ordered.map((key) => (
              <th key={key} scope="col" className={`border-b border-line px-2 py-1.5 ${key === "quantity" || key === "price" ? "text-right" : "text-left"}`}>
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {ordered.map((key) => (
                <td key={key} className={`border-b border-line px-2 py-1 align-top ${key === "quantity" || key === "price" ? "num" : ""}`}>
                  {cell(key, row[key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function cell(key: string, value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") return <span className="text-muted">—</span>;
  if (key === "at" || key.endsWith("_at")) return <span className="tabular">{formatDate(value) ?? String(value)}</span>;
  if (key === "price") return formatPrice(value) ?? String(value);
  if (key === "quantity") return formatQuantity(value) ?? String(value);
  if (typeof value === "object") return <span className="code break-all">{JSON.stringify(value)}</span>;
  return String(value);
}

function Comparison(props: { comparison: Record<string, unknown> }) {
  const planned = (props.comparison.planned || {}) as Record<string, unknown>;
  const actual = (props.comparison.actual || {}) as Record<string, unknown>;
  const deltas = (props.comparison.deltas || {}) as Record<string, unknown>;
  const keys = Array.from(new Set([...Object.keys(planned), ...Object.keys(actual), ...Object.keys(deltas)]));
  if (keys.length === 0) return <p className="text-[12px] text-muted">No comparable fields were returned.</p>;
  return (
    <div className="overflow-auto rounded-[4px] border border-line">
      <table className="gtf-table w-full border-collapse text-[11.5px]">
        <thead className="bg-surface-2">
          <tr>
            <th scope="col" className="border-b border-line px-2 py-1.5 text-left">Field</th>
            <th scope="col" className="border-b border-line px-2 py-1.5 text-right">Planned</th>
            <th scope="col" className="border-b border-line px-2 py-1.5 text-right">Actual</th>
            <th scope="col" className="border-b border-line px-2 py-1.5 text-right">Delta</th>
          </tr>
        </thead>
        <tbody>
          {keys.map((key) => (
            <tr key={key}>
              <td className="border-b border-line px-2 py-1">{key}</td>
              <td className="num border-b border-line px-2">{show(planned[key])}</td>
              <td className="num border-b border-line px-2">{show(actual[key])}</td>
              <td className="num border-b border-line px-2">{show(deltas[key])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function show(value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") return <span className="text-muted">—</span>;
  if (typeof value === "object") return <span className="code">{JSON.stringify(value)}</span>;
  return String(value);
}

function Attachments(props: { entryId: string; rows: unknown }) {
  const app = useAppState();
  const [preview, setPreview] = useState<{ id: string; src: string; name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rows = Array.isArray(props.rows) ? (props.rows as Array<Record<string, unknown>>) : [];
  if (rows.length === 0) return <p className="text-[12px] text-muted">No attachments.</p>;
  async function open(id: string) {
    const result = await app.request<{ content_type?: string; content_base64?: string; filename?: string }>(
      `/api/v1/journal/${encodeURIComponent(props.entryId)}/attachments/${encodeURIComponent(id)}`,
    );
    if (!result.ok) {
      setError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    const data = result.envelope.data;
    if (!data.content_type?.startsWith("image/") || !data.content_base64) {
      setError("The attachment is not an image that can be previewed.");
      return;
    }
    setError(null);
    setPreview({ id, src: `data:${data.content_type};base64,${data.content_base64}`, name: data.filename ?? id });
  }
  return (
    <div className="space-y-2">
      <ul className="space-y-1 text-[12px]">
        {rows.map((row, index) => {
          const id = text(row.attachment_id);
          return (
            <li key={id ?? index} className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{text(row.filename) ?? id ?? "attachment"}</span>
              <span className="text-muted">{formatDate(row.at) ?? ""}</span>
              {id ? (
                <Button size="sm" type="button" onClick={() => void open(id)}>
                  View
                </Button>
              ) : null}
            </li>
          );
        })}
      </ul>
      {error ? <p className="text-[12px] text-[var(--gtf-fail)]">{error}</p> : null}
      {preview ? (
        <figure className="rounded-[4px] border border-line p-2">
          <img src={preview.src} alt={`Attachment ${preview.name}`} className="max-h-80 w-auto" />
          <figcaption className="mt-1 text-[11px] text-muted">{preview.name}. Owner-attached; not an eligibility input.</figcaption>
        </figure>
      ) : null}
    </div>
  );
}
