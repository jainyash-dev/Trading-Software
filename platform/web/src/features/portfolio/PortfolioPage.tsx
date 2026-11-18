import { useEffect, useState } from "react";
import { Button, DataTable, EmptyState, KeyValue, Meter, Page, Panel, ProvenanceBadge } from "../../design/components";
import { formatInr, formatPrice, formatQuantity, toNumber } from "../../design/format";
import { useAppState } from "../../state/store";
import { MarkState } from "../risk/RiskPage";

type Zone = Record<string, unknown> & { id: string };

function raw(value: unknown): string {
  if (value === null || value === undefined || value === "") return "UNAVAILABLE";
  return String(value);
}

/** Money when numeric, otherwise the raw state text (UNAVAILABLE stays UNAVAILABLE, never 0). */
function money(value: unknown, state?: unknown): string {
  if (state === "UNAVAILABLE") return "UNAVAILABLE";
  return formatInr(value) ?? raw(value);
}

function price(value: unknown): string {
  return formatPrice(value) ?? raw(value);
}

/**
 * P10-7 Portfolio. Counts and valuation come from GET /api/v1/portfolio (research journal plus
 * the last accepted EOD close). Nothing is computed in the browser. There is no order.
 */
export function PortfolioPage() {
  const app = useAppState();
  const [book, setBook] = useState<Record<string, unknown> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (app.connection !== "connected") {
      setBook(null);
      setLoadError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    void app.request<Record<string, unknown>>("/api/v1/portfolio").then((result) => {
      if (result.ok) {
        setBook(result.envelope.data);
        setLoadError(null);
      } else {
        setBook(null);
        setLoadError(result.error.message);
      }
      setLoading(false);
    });
  }, [app.connection, app.request]);

  const zones: Zone[] = Array.isArray(book?.zones)
    ? (book.zones as Array<Record<string, unknown>>).map((zone, index) => ({ ...zone, id: String(zone.entry_id ?? zone.zone_id ?? index) }))
    : [];
  const openZones = zones.filter((zone) => zone.counts_as_open === true);
  const valuationState = String(book?.valuation_state ?? "");

  return (
    <Page
      eyebrow="Trading"
      title="Portfolio"
      description="Counts come from the research journal only. Valuation uses the last accepted EOD close and prints that date. A STALE mark is not a live quote. Sector and live drawdown stay UNAVAILABLE. There is no order."
      meta={
        book ? (
          <>
            {valuationState === "STALE" ? <ProvenanceBadge kind="STALE" /> : null}
            {valuationState === "UNAVAILABLE" ? <ProvenanceBadge kind="UNAVAILABLE" /> : null}
            {String(book.research_use ?? "").includes("FIXTURE") ? <ProvenanceBadge kind="FIXTURE" /> : <ProvenanceBadge kind="EXPLORATORY" title="EOD marks are not P0 certified" />}
          </>
        ) : null
      }
      actions={
        <>
          <Button type="button" onClick={() => app.navigate("risk")}>
            Risk overview
          </Button>
          <Button type="button" onClick={() => app.navigate("journal")}>
            Trading journal
          </Button>
        </>
      }
    >
      {app.connection !== "connected" ? (
        <EmptyState title="Portfolio unavailable" reason="The API session is not authenticated. Counts from a previous session are not shown." />
      ) : null}
      {app.connection === "connected" && loadError ? <EmptyState title="Portfolio unavailable" reason={loadError} /> : null}
      {app.connection === "connected" && loading && !book && !loadError ? (
        <EmptyState title="Loading portfolio" reason="Reading the research journal. Canonical counts are not invented in the browser." />
      ) : null}
      {app.connection === "connected" && !loading && !book && !loadError ? <EmptyState title="Portfolio unavailable" reason="The journal has not been read." /> : null}

      {book ? (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-3 2xl:grid-cols-6">
            <Kpi label="Trades this month" sub={`IST month ${raw(book.ist_month)}. Exits do not restore it.`}>
              <span data-testid="portfolio-monthly-count">{raw(book.trades_triggered_this_month)}</span>
              <span className="text-[13px] font-normal text-muted">{" of "}</span>
              <span data-testid="portfolio-monthly-cap">{raw(book.monthly_cap)}</span>
              <Meter value={toNumber(book.trades_triggered_this_month)} max={toNumber(book.monthly_cap)} label="Monthly cap usage" />
            </Kpi>
            <Kpi label="Open positions" sub="Independent cap from the monthly allowance.">
              <span data-testid="portfolio-open-count">{raw(book.open_positions)}</span>
              <span className="text-[13px] font-normal text-muted">{" of "}</span>
              <span data-testid="portfolio-open-cap">{raw(book.open_position_cap)}</span>
              <Meter value={toNumber(book.open_positions)} max={toNumber(book.open_position_cap)} label="Open position cap usage" />
            </Kpi>
            <Kpi label="Portfolio valuation" sub="Last accepted EOD close">
              <span data-testid="portfolio-valuation">{money(book.valuation, book.valuation_state)}</span>
            </Kpi>
            <Kpi label="Unrealised PnL" sub="Against EOD marks">
              <span data-testid="portfolio-unrealised" className={pnlTone(book.unrealised_pnl)}>
                {money(book.unrealised_pnl, book.valuation_state === "UNAVAILABLE" && book.unrealised_pnl == null ? "UNAVAILABLE" : undefined)}
              </span>
            </Kpi>
            <Kpi label="Market exposure" sub={`State ${raw(book.exposure_state)}`}>
              <span data-testid="portfolio-exposure">{money(book.exposure, book.exposure_state)}</span>
            </Kpi>
            <Kpi label="Open risk" sub={`To recorded stops · ${raw(book.portfolio_risk_state)}`}>
              <span data-testid="portfolio-open-risk">{money(book.portfolio_risk, book.portfolio_risk_state)}</span>
            </Kpi>
          </div>

          <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_300px]">
            <Panel title="Positions and zone allowances" subtitle="EOD only. Not a live quote. No price was invented. Each zone allows one order (ONE_ORDER_PER_ZONE)." flush>
              <div className="p-3.5">
                {openZones.length === 0 ? (
                  <p className="mb-3 text-[12.5px] text-muted" data-testid="portfolio-empty-open">
                    No open journal position at this reading. A closed trade does not free the monthly allowance. Refused journal operations are not shown as open positions.
                  </p>
                ) : null}
                {zones.length ? (
                  <DataTable<Zone>
                    caption="Positions"
                    rows={zones}
                    columns={[
                      {
                        key: "symbol",
                        header: "Symbol",
                        sortValue: (zone) => String(zone.symbol),
                        render: (zone) => (
                          <span data-testid={`portfolio-zone-${String(zone.symbol)}-${String(zone.zone_id)}`}>
                            <span className="font-semibold">{String(zone.symbol)}</span>
                            <span className="code block text-muted">{String(zone.zone_id)}</span>
                          </span>
                        ),
                      },
                      {
                        key: "state",
                        header: "State",
                        render: (zone) => (
                          <span title={String(zone.reason || "No allowance reason was stored.")}>
                            {String(zone.state || "UNKNOWN")}
                            <span className="block text-[11px] text-muted">{zone.counts_as_open === true ? "Open position" : "Allowance held"}</span>
                          </span>
                        ),
                      },
                      { key: "qty", header: "Open qty", numeric: true, render: (zone) => <span data-testid={`portfolio-open-qty-${String(zone.symbol)}`}>{formatQuantity(zone.open_quantity) ?? raw(zone.open_quantity)}</span> },
                      { key: "avg", header: "Avg entry", numeric: true, render: (zone) => <span data-testid={`portfolio-avg-entry-${String(zone.symbol)}`}>{price(zone.average_entry_price)}</span> },
                      { key: "stop", header: "Stop (plan / locked)", numeric: true, render: (zone) => `${price(zone.planned_stop)} / ${price(zone.locked_stop)}` },
                      { key: "target", header: "Target", numeric: true, render: (zone) => price(zone.planned_target) },
                      { key: "realised", header: "Realised", numeric: true, render: (zone) => <span className={pnlTone(zone.realised_pnl)}>{money(zone.realised_pnl)}</span> },
                      { key: "unrealised", header: "Unrealised", numeric: true, render: (zone) => <span className={pnlTone(zone.unrealised_pnl ?? zone.unrealised)}>{money(zone.unrealised_pnl ?? zone.unrealised)}</span> },
                      {
                        key: "risk",
                        header: "Position risk",
                        numeric: true,
                        render: (zone) => <span data-testid={`portfolio-position-risk-${String(zone.symbol)}`}>{money(zone.position_risk, zone.position_risk_state)}</span>,
                      },
                      {
                        key: "mark",
                        header: "EOD mark",
                        numeric: true,
                        render: (zone) => <span data-testid={`portfolio-mark-${String(zone.symbol)}`}>{zone.valuation_state === "UNAVAILABLE" ? "UNAVAILABLE" : price(zone.valuation)}</span>,
                      },
                      {
                        key: "date",
                        header: "Mark date",
                        render: (zone) => (
                          <span className="tabular" data-testid={`portfolio-price-date-${String(zone.symbol)}`}>
                            {raw(zone.price_date)}
                          </span>
                        ),
                      },
                      {
                        key: "markstate",
                        header: "Mark state",
                        render: (zone) => (
                          <span data-testid={`portfolio-mark-state-${String(zone.symbol)}`}>
                            <MarkState value={zone.valuation_state} />
                          </span>
                        ),
                      },
                      {
                        key: "journal",
                        header: "",
                        render: (zone) =>
                          zone.entry_id != null ? (
                            <Button size="sm" type="button" onClick={() => app.navigate("journal", { entry: String(zone.entry_id) })}>
                              Journal
                            </Button>
                          ) : null,
                      },
                    ]}
                  />
                ) : null}
              </div>
            </Panel>
            <Panel title="Valuation and data">
              <KeyValue
                rows={[
                  ["Valuation state", <span data-testid="portfolio-valuation-state">{raw(book.valuation_state)}</span>],
                  ["Sector", <span data-testid="portfolio-sector">{raw(book.sector_state)}</span>],
                  ["Drawdown", <span data-testid="portfolio-drawdown">{raw(book.drawdown_state)}</span>],
                  ["Research use", <span data-testid="portfolio-research-use" className="code">{raw(book.research_use)}</span>],
                ]}
              />
              {book.valuation_reason ? (
                <p className="text-[12px] text-muted" data-testid="portfolio-valuation-reason">
                  {String(book.valuation_reason)}
                </p>
              ) : null}
              <p className="text-[12px] text-muted" data-testid="portfolio-note">
                {String(book.note || "")}
              </p>
            </Panel>
          </div>
        </>
      ) : null}
    </Page>
  );
}

function Kpi(props: { label: string; sub: string; children: React.ReactNode }) {
  return (
    <div className="panel min-w-0 px-3.5 py-3">
      <p className="eyebrow">{props.label}</p>
      <div className="mt-1 text-[19px] font-semibold leading-7 tabular">{props.children}</div>
      <p className="mt-1 text-[11.5px] leading-4 text-muted">{props.sub}</p>
    </div>
  );
}

function pnlTone(value: unknown): string {
  const number = toNumber(value);
  if (number === null || number === 0) return "";
  return number > 0 ? "text-[var(--gtf-ok)]" : "text-[var(--gtf-fail)]";
}
