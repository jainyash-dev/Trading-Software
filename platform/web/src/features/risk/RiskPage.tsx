import { Button, DataTable, EmptyState, Metric, Meter, Page, Panel, ProvenanceBadge, Skeleton, Unavailable } from "../../design/components";
import { formatInr, formatPrice, formatQuantity, toNumber } from "../../design/format";
import { useAppState } from "../../state/store";
import { ErrorLine } from "../shared/ui";
import { dataOf, useApi } from "../shared/useApi";

type Row = Record<string, unknown> & { id: string };

/**
 * P10-7 Risk Overview. Every figure is returned by /api/v1/portfolio (journal-derived, EOD valuation)
 * or /api/v1/settings (owner inputs). The browser computes no risk, exposure or P&L.
 */
export function RiskPage() {
  const app = useAppState();
  const live = app.connection === "connected";
  const portfolio = useApi<Record<string, unknown>>("/api/v1/portfolio");
  const settings = useApi<Record<string, unknown>>("/api/v1/settings");
  const book = dataOf(portfolio);
  const prefs = dataOf(settings);
  const monthly = toNumber(book?.trades_triggered_this_month);
  const monthlyCap = toNumber(book?.monthly_cap);
  const open = toNumber(book?.open_positions);
  const openCap = toNumber(book?.open_position_cap);
  const zones: Row[] = Array.isArray(book?.zones)
    ? (book.zones as Array<Record<string, unknown>>).filter((zone) => zone.counts_as_open === true).map((zone, index) => ({ ...zone, id: String(zone.entry_id ?? `${zone.symbol}-${index}`) }))
    : [];
  const stateValue = (value: unknown, state: unknown) => (state === "UNAVAILABLE" ? null : formatInr(value));

  return (
    <Page
      eyebrow="Trading"
      title="Risk Overview"
      description="The two owner caps (10 trades per IST month, 10 open positions) are independent. Risk and exposure are read from the journal-derived portfolio and marked to the last accepted EOD close. Sector exposure and live drawdown have no data source and stay unavailable."
      meta={book ? <ProvenanceBadge kind={book.valuation_state === "STALE" ? "STALE" : book.valuation_state === "UNAVAILABLE" ? "UNAVAILABLE" : "EXPLORATORY"} title={`valuation_state ${String(book.valuation_state ?? "unknown")}`} /> : null}
      actions={
        <Button type="button" onClick={() => app.navigate("portfolio")}>
          Open portfolio
        </Button>
      }
    >
      {!live ? <EmptyState title="Risk overview unavailable" reason="The API session is not connected. Figures from a previous session are not shown." /> : null}
      {portfolio.state === "loading" ? <Skeleton rows={3} /> : null}
      {portfolio.state === "error" ? <ErrorLine error={portfolio.error} /> : null}
      {book ? (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <Metric label="Trades this IST month" value={monthly === null ? null : `${monthly} of ${monthlyCap ?? "?"}`} sub={`Month ${String(book.ist_month ?? "unavailable")}. A closed trade does not free the monthly allowance.`}>
              <Meter value={monthly} max={monthlyCap} label="Monthly trade cap usage" />
            </Metric>
            <Metric label="Open positions" value={open === null ? null : `${open} of ${openCap ?? "?"}`} sub="Independent of the monthly cap.">
              <Meter value={open} max={openCap} label="Open position cap usage" />
            </Metric>
            <Metric label="Open risk" value={stateValue(book.portfolio_risk, book.portfolio_risk_state)} sub={`State ${String(book.portfolio_risk_state ?? "unavailable")}. Loss to recorded stops.`} />
            <Metric label="Market exposure" value={stateValue(book.exposure, book.exposure_state)} sub={`State ${String(book.exposure_state ?? "unavailable")}. EOD marks, not live.`} />
          </div>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <Panel title="Position risk" subtitle="Open journal positions only. Stops are the recorded plan or locked stop." flush>
              <div className="p-3.5">
                {zones.length === 0 ? (
                  <EmptyState title="No open position" reason="The journal has no open position at this reading. Risk is not assumed to be zero for unrecorded trades." />
                ) : (
                  <DataTable<Row>
                    caption="Position risk"
                    rows={zones}
                    columns={[
                      { key: "symbol", header: "Symbol", sortValue: (row) => String(row.symbol), render: (row) => <span className="font-semibold">{String(row.symbol)}</span> },
                      { key: "qty", header: "Open qty", numeric: true, render: (row) => formatQuantity(row.open_quantity) ?? <Unavailable /> },
                      { key: "avg", header: "Avg entry", numeric: true, render: (row) => formatPrice(row.average_entry_price) ?? <Unavailable /> },
                      { key: "stop", header: "Stop (plan / locked)", numeric: true, render: (row) => `${formatPrice(row.planned_stop) ?? "—"} / ${formatPrice(row.locked_stop) ?? "—"}` },
                      { key: "risk", header: "Position risk", numeric: true, render: (row) => (row.position_risk_state === "UNAVAILABLE" ? <Unavailable /> : formatInr(row.position_risk) ?? <Unavailable />) },
                      { key: "mark", header: "EOD mark", numeric: true, render: (row) => (row.valuation_state === "UNAVAILABLE" ? <Unavailable /> : formatPrice(row.valuation) ?? <Unavailable />) },
                      { key: "date", header: "Mark date", render: (row) => <span className="tabular">{String(row.price_date ?? "unavailable")}</span> },
                      { key: "state", header: "Mark state", render: (row) => <MarkState value={row.valuation_state} /> },
                    ]}
                  />
                )}
              </div>
            </Panel>
            <div className="space-y-4">
              <Panel title="Owner risk inputs" subtitle="From Settings. Not recalculated here.">
                {settings.state === "error" ? <ErrorLine error={settings.error} /> : null}
                <dl className="space-y-1.5 text-[12.5px]">
                  <Line label="Capital" value={formatInr(prefs?.capital)} />
                  <Line label="Risk per trade" value={toNumber(prefs?.rpt_pct) === null ? null : `${String(prefs?.rpt_pct)}%`} />
                  <Line label="Risk stage" value={typeof prefs?.risk_stage === "string" ? prefs.risk_stage : null} />
                </dl>
                <Button type="button" size="sm" onClick={() => app.navigate("settings")}>
                  Edit in Settings
                </Button>
              </Panel>
              <Panel title="Not available">
                <dl className="space-y-1.5 text-[12.5px]">
                  <Line label="Sector exposure" value={null} note={String(book.sector_state ?? "UNAVAILABLE")} />
                  <Line label="Drawdown" value={null} note={String(book.drawdown_state ?? "UNAVAILABLE")} />
                </dl>
                <p className="text-[11.5px] text-muted">No approved sector source (D6) and no live price feed. These are not zero.</p>
              </Panel>
            </div>
          </div>
          {book.valuation_reason ? <p className="text-[12px] text-muted">{String(book.valuation_reason)}</p> : null}
        </>
      ) : null}
    </Page>
  );
}

function Line(props: { label: string; value: string | null; note?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line pb-1.5 last:border-b-0">
      <dt className="text-muted">{props.label}</dt>
      <dd className="tabular">{props.value ?? (props.note ? <span className="text-muted">— {props.note}</span> : <Unavailable />)}</dd>
    </div>
  );
}

export function MarkState({ value }: { value: unknown }) {
  const state = String(value ?? "UNAVAILABLE");
  if (state === "STALE") return <ProvenanceBadge kind="STALE" />;
  if (state === "UNAVAILABLE") return <ProvenanceBadge kind="UNAVAILABLE" />;
  return <span className="text-[11.5px] font-medium">{state}</span>;
}
