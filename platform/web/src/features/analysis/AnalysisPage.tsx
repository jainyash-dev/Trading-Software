import { useEffect, useMemo, useState, type ReactNode } from "react";
import { readViewQuery, writeViewQuery } from "../../navigation/query";
import { CandleChart, type ChartController } from "../../chart/CandleChart";
import { prepareSeries, type DrawingKind, type DrawingRecord } from "../../chart/model";
import { DEFAULT_ZONE_VISIBILITY, zonesFromStored, type ZoneVisibility } from "../../chart/zones";
import { analysisEvidence, type Fetched } from "../../chart/evidence";
import { planOverlayFromRecords } from "../../chart/plans";
import { Button, EmptyState, KeyValue, Notices, Page, Panel, ProvenanceBadge, Segmented, Skeleton, StatusBadge, Unavailable, type Tone } from "../../design/components";
import { formatPrice } from "../../design/format";
import { useAppState } from "../../state/store";
import type { Candle, CandlePayload, Instrument, ScanListData, SymbolBundle, Timeframe, ZoneView } from "../../types/contracts";
import { Warning } from "../shared/ui";
import { dataOf, useApi } from "../shared/useApi";

function newKey(): string {
  return crypto.randomUUID();
}

function parseVolume(raw: string | number | null | undefined): number | null {
  if (raw === null || raw === undefined || raw === "") return null;
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0) return null;
  return value;
}

function drawingFromApi(row: Record<string, unknown>, fallback: { symbol: string; timeframe: Timeframe }): DrawingRecord | null {
  const geometry = (row.geometry || {}) as Record<string, unknown>;
  const kind = String(geometry.type || "") as DrawingKind;
  if (!["horizontal", "trend", "rectangle", "text"].includes(kind)) return null;
  const points = Array.isArray(geometry.points)
    ? geometry.points
        .map((point) => {
          const item = point as Record<string, unknown>;
          const time = String(item.time || "");
          const price = Number(item.price);
          if (!time || !Number.isFinite(price)) return null;
          return { time, price };
        })
        .filter((point): point is { time: string; price: number } => point !== null)
    : [];
  if (points.length === 0 && kind !== "text") return null;
  return {
    drawingId: String(row.drawing_id || newKey()),
    symbol: String(row.symbol || fallback.symbol),
    timeframe: (String(row.timeframe || fallback.timeframe) as Timeframe) || fallback.timeframe,
    asOf: row.as_of ? String(row.as_of) : null,
    kind,
    points,
    text: String(geometry.text || ""),
    persistence: "PLATFORM_DB",
    version: Number(row.version || 1),
  };
}

const DESCRIPTION = "Candles and zones come from the stored scan and the candle route. The chart does not score eligibility.";

export function AnalysisPage() {
  const app = useAppState();
  const view = useMemo(() => readViewQuery(app.queryString), [app.queryString]);
  const symbol = view.symbol;
  const scan = view.scan;
  const asOfFromQuery = view.asOf;
  const datasetFromQuery = view.datasetId;
  const timeframe: Timeframe = view.timeframe || "D";
  const [candles, setCandles] = useState<CandlePayload | null>(null);
  const [bundle, setBundle] = useState<SymbolBundle | null>(null);
  const [explain, setExplain] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fixture, setFixture] = useState(false);
  const [controller, setController] = useState<ChartController | null>(null);
  const [drawings, setDrawings] = useState<DrawingRecord[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null);
  const [visibility, setVisibility] = useState<ZoneVisibility>(DEFAULT_ZONE_VISIBILITY);
  const [drawingError, setDrawingError] = useState<string | null>(null);
  const [resolvedAsOf, setResolvedAsOf] = useState("");
  const [resolvedDataset, setResolvedDataset] = useState("");
  const [resolvedFromScan, setResolvedFromScan] = useState(false);
  const [identity, setIdentity] = useState<Instrument | null>(null);
  const [fetched, setFetched] = useState<{
    candles: Fetched<CandlePayload> | null;
    bundle: Fetched<SymbolBundle> | null;
    explain: Fetched<unknown> | null;
    plans: Fetched<unknown> | null;
  }>({ candles: null, bundle: null, explain: null, plans: null });
  const [planRecords, setPlanRecords] = useState<Array<Record<string, unknown>>>([]);
  const [showPlans, setShowPlans] = useState(true);

  const patchQuery = (patch: Partial<Record<string, string | null>>) => {
    const qs = writeViewQuery(app.queryString, patch);
    window.location.hash = qs ? `/analysis?${qs}` : "/analysis";
  };

  useEffect(() => {
    if (app.connection !== "connected" || !symbol) {
      setIdentity(null);
      return;
    }
    let cancelled = false;
    void app.request<{ instruments?: Array<Record<string, unknown>> }>("/api/v1/instruments", { query: { query: symbol } }).then((result) => {
      if (cancelled || !result.ok) return;
      const match = (result.envelope.data.instruments ?? []).find((row) => String(row.symbol).toUpperCase() === symbol);
      setIdentity(
        match
          ? {
              symbol,
              name: typeof match.name === "string" && match.name ? match.name : null,
              isin: typeof match.isin === "string" && match.isin ? match.isin : null,
              verified: match.verified === true,
            }
          : null,
      );
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.connection, symbol]);

  useEffect(() => {
    if (app.connection !== "connected" || !symbol || !scan) return;
    if (view.rejected.includes("as_of") || view.rejected.includes("symbol") || view.rejected.includes("scan")) return;
    const fixtures = view.fixtures ? { include_fixtures: true } : {};
    let cancelled = false;
    const requestId = `${symbol}|${timeframe}|${asOfFromQuery}|${datasetFromQuery}|${scan}|${view.fixtures ? 1 : 0}`;
    setLoading(true);
    setError(null);
    setCandles(null);
    setBundle(null);
    setExplain(null);
    setFixture(false);
    setSelectedZoneId(null);
    setDrawingError(null);
    setResolvedAsOf("");
    setResolvedDataset("");
    setResolvedFromScan(false);
    setFetched({ candles: null, bundle: null, explain: null, plans: null });
    setPlanRecords([]);
    void (async () => {
      // P2-IR-2: never bind candles to health.last_scan when the URL names a different scan.
      // Missing as_of/dataset come only from the target scan envelope.
      let asOf = asOfFromQuery;
      let dataset = datasetFromQuery;
      let fromScan = false;
      if (!asOf || !dataset) {
        const stored = await app.request<{ as_of?: string; dataset_id?: string | null }>(`/api/v1/scans/${encodeURIComponent(scan)}`, {
          query: { ...fixtures },
        });
        if (cancelled) return;
        if (!stored.ok) {
          setLoading(false);
          setError(stored.error.message);
          setFetched({
            candles: null,
            bundle: { ok: false, status: stored.status, code: stored.error.code, message: stored.error.message },
            explain: null,
            plans: null,
          });
          return;
        }
        asOf = asOf || String(stored.envelope.data.as_of || "");
        dataset = dataset || String(stored.envelope.data.dataset_id || "");
        fromScan = true;
      }
      if (cancelled) return;
      if (!asOf || !dataset) {
        setLoading(false);
        setError("as_of and dataset_id are required. Open the symbol from the stored scan so the address carries them.");
        return;
      }
      setResolvedAsOf(asOf);
      setResolvedDataset(dataset);
      setResolvedFromScan(fromScan);
      const candle = await app.request<CandlePayload>("/api/v1/candles", {
        query: { symbol, timeframe, as_of: asOf, dataset_id: dataset },
      });
      const packed = await app.request<SymbolBundle>(`/api/v1/symbols/${symbol}/bundle`, {
        query: { scan_key: scan, as_of: asOf, dataset_id: dataset, ...fixtures },
      });
      const words = await app.request<{ answer_lines?: string[]; result?: string }>(`/api/v1/symbols/${symbol}/explain`, {
        query: { scan_key: scan, ...fixtures },
      });
      const listed = await app.request<{ drawings?: Array<Record<string, unknown>> }>("/api/v1/drawings", {
        query: { symbol, timeframe },
      });
      // FR-4.9: canonical plan records for this symbol and this stored scan. Display only.
      const planned = await app.request<{ plans?: Array<Record<string, unknown>> }>("/api/v1/plans", {
        query: { symbol, scan_key: scan },
      });
      if (cancelled) return;
      const stillCurrent = `${symbol}|${timeframe}|${asOfFromQuery}|${datasetFromQuery}|${scan}|${view.fixtures ? 1 : 0}` === requestId;
      if (!stillCurrent) return;
      setLoading(false);
      setFixture(Boolean(candle.ok && candle.envelope.meta.fixture) || Boolean(packed.ok && packed.envelope.meta.fixture));
      if (!candle.ok) setError(candle.error.message);
      else setCandles(candle.envelope.data);
      if (packed.ok) setBundle(packed.envelope.data);
      else setError((current) => current || packed.error.message);
      if (words.ok) setExplain(words.envelope.data.answer_lines || [words.envelope.data.result || "NOT_IN_SCAN"]);
      else setExplain([words.error.message]);
      const asFetched = <T,>(result: typeof candle | typeof packed | typeof words | typeof planned): Fetched<T> =>
        result.ok
          ? { ok: true, data: result.envelope.data as T, fixture: Boolean(result.envelope.meta.fixture) }
          : { ok: false, status: result.status, code: result.error.code, message: result.error.message };
      setFetched({
        candles: asFetched<CandlePayload>(candle),
        bundle: asFetched<SymbolBundle>(packed),
        explain: asFetched<unknown>(words),
        plans: asFetched<unknown>(planned),
      });
      setPlanRecords(planned.ok ? planned.envelope.data.plans || [] : []);
      if (listed.ok) {
        const rows = (listed.envelope.data.drawings || [])
          .map((row) => drawingFromApi(row, { symbol, timeframe }))
          .filter((row): row is DrawingRecord => row !== null);
        setDrawings(rows);
      } else {
        setDrawings([]);
        setDrawingError(listed.error.message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [app, symbol, scan, asOfFromQuery, datasetFromQuery, timeframe, view.fixtures, view.rejected]);

  const series = useMemo(() => {
    const rows: Candle[] = [];
    const skipped: string[] = [];
    for (const row of candles?.candles || []) {
      const open = Number(row.open);
      const high = Number(row.high);
      const low = Number(row.low);
      const close = Number(row.close);
      if (!row.session_date || [open, high, low, close].some((value) => !Number.isFinite(value))) {
        if (row.session_date) skipped.push(row.session_date);
        continue;
      }
      rows.push({ time: row.session_date, open, high, low, close, volume: parseVolume(row.volume) });
    }
    const prepared = prepareSeries(rows);
    return { prepared, skipped };
  }, [candles]);

  const zones = useMemo(() => zonesFromStored(bundle?.stored as Record<string, unknown> | undefined, symbol, visibility), [bundle, symbol, visibility]);
  const selectedZone = zones.find((zone) => zone.engineId === selectedZoneId) || null;
  const planOverlay = useMemo(() => planOverlayFromRecords(planRecords, { symbol, scanKey: scan }), [planRecords, symbol, scan]);
  const evidence = useMemo(
    () =>
      analysisEvidence({
        symbol,
        datasetId: resolvedDataset || datasetFromQuery,
        candles: fetched.candles,
        bundle: fetched.bundle,
        explain: fetched.explain,
        plans: fetched.plans,
        series: { ok: series.prepared.ok, count: series.prepared.candles.length },
      }),
    [symbol, resolvedDataset, datasetFromQuery, fetched, series],
  );
  const showVolume = candles?.volume_state === "PRESENT" || candles?.volume_state === "PARTIAL";
  const quality = candles?.data_quality;
  const researchUse = quality?.research_use || (fixture ? "FIXTURE_NOT_MARKET_DATA" : null);
  const lastCandle = series.prepared.ok ? series.prepared.candles.at(-1) : undefined;
  const candidates = (bundle?.stored?.candidates ?? []) as Array<Record<string, unknown>>;

  if (view.rejected.length) {
    return (
      <Page eyebrow="Research" title="Stock Analysis" description={DESCRIPTION}>
        <Warning>The address has a query value this screen will not use. Open the symbol again from the stored scan.</Warning>
      </Page>
    );
  }
  if (!symbol || !scan) {
    return <NoScan symbol={symbol} />;
  }

  const notices: Array<{ key: string; tone?: Tone; content: ReactNode }> = [];
  if (researchUse) notices.push({ key: "use", content: `${researchUse}. Certified: ${String(quality?.certified ?? false)}. Chart retrieval is not P0 certification.` });
  if (resolvedFromScan) notices.push({ key: "resolved", content: "as_of or dataset_id was read from the named stored scan envelope because the address omitted it. They are not taken from a different last_scan." });
  if (fixture) notices.push({ key: "fixture", content: "FIXTURE_NOT_MARKET_DATA. These candles are not an NSE result." });
  if (bundle?.completeness && bundle.completeness !== "COMPLETE") notices.push({ key: "complete", content: `This scan is ${bundle.completeness}. It is not a complete scan.` });
  if (candles?.limitations?.length) notices.push({ key: "candle-limits", content: `Candle limitations: ${candles.limitations.join(", ")}` });
  if (candles?.missing_sessions?.length)
    notices.push({
      key: "missing",
      content: `Missing sessions reported (${candles.missing_sessions.length}). Not filled. Not assumed to be holidays: ${candles.missing_sessions.slice(0, 8).join(", ")}${candles.missing_sessions.length > 8 ? "…" : ""}`,
    });
  if (candles?.invalid_candles?.length || series.skipped.length) {
    const items = [...(candles?.invalid_candles || []).map((row) => `${row.session_date || "?"} (${(row.codes || []).join("/")})`), ...series.skipped.map((day) => `${day} (client)`)];
    notices.push({ key: "invalid", content: `Invalid or undrawable candle rows were excluded (not filled): ${items.slice(0, 8).join(", ")}${items.length > 8 ? "…" : ""}` });
  }
  if (bundle?.limitations?.length) notices.push({ key: "bundle-limits", content: `Scan limitations: ${bundle.limitations.join(", ")}` });

  return (
    <Page
      eyebrow="Research · Stock Analysis"
      title={`${symbol} analysis`}
      description={DESCRIPTION}
      meta={
        <>
          <span className="text-[12.5px] text-ink-2">{identity?.name ?? "Name unavailable"}</span>
          <span className="code text-muted">ISIN {identity?.isin ?? "unavailable"}</span>
          <span className={`text-[11.5px] ${identity?.verified ? "text-muted" : "text-[var(--gtf-manual)]"}`}>identity {identity ? (identity.verified ? "verified" : "unverified") : "unknown"}</span>
          {fixture ? <ProvenanceBadge kind="FIXTURE" /> : quality ? <ProvenanceBadge kind={quality.certified ? "CERTIFIED" : "EXPLORATORY"} title={quality.research_use} /> : null}
        </>
      }
      actions={
        <div className="flex items-end gap-4">
          <div className="text-right">
            <p className="eyebrow">Close at as-of · EOD, not live</p>
            <p className="tabular text-[20px] font-semibold leading-7">{lastCandle ? formatPrice(lastCandle.close) : <span className="text-[13px] font-normal text-muted">— Unavailable</span>}</p>
            <p className="tabular text-[11px] text-muted">{lastCandle ? `${lastCandle.time} · ${timeframe} candle` : "No drawable candle"}</p>
          </div>
        </div>
      }
    >
      <div className="panel flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2">
        <Segmented
          label="Timeframe"
          value={timeframe}
          options={[
            { value: "M", label: "M", title: "Monthly" },
            { value: "W", label: "W", title: "Weekly" },
            { value: "D", label: "D", title: "Daily" },
          ]}
          onChange={(item) =>
            patchQuery({
              timeframe: item,
              symbol,
              scan,
              as_of: resolvedAsOf || asOfFromQuery || null,
              dataset_id: resolvedDataset || datasetFromQuery || null,
            })
          }
        />
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Zone timeframe visibility">
          {(["M", "W", "D"] as const).map((item) => (
            <Button key={`z-${item}`} size="sm" type="button" aria-pressed={visibility[item]} onClick={() => setVisibility((current) => ({ ...current, [item]: !current[item] }))}>
              {item} zones
            </Button>
          ))}
          <Button size="sm" type="button" aria-pressed={showPlans} onClick={() => setShowPlans((current) => !current)}>
            Plan lines
          </Button>
        </div>
        <div className="ml-auto flex gap-1.5">
          <Button size="sm" type="button" onClick={() => controller?.zoom(-1)} aria-label="Zoom out">
            −
          </Button>
          <Button size="sm" type="button" onClick={() => controller?.zoom(1)} aria-label="Zoom in">
            +
          </Button>
          <Button size="sm" type="button" onClick={() => controller?.fit()}>
            Fit
          </Button>
        </div>
      </div>
      <p className="text-[11.5px] text-muted">
        Dataset <span className="code" title={resolvedDataset || datasetFromQuery}>{(resolvedDataset || datasetFromQuery || "unavailable").slice(0, 12)}</span>. As of {resolvedAsOf || asOfFromQuery || "unavailable"}. Scan{" "}
        <span className="code">{scan}</span>. Adjusted prices: false. Completeness {bundle?.completeness || "unavailable"}. Volume {candles?.volume_state || "unavailable"}
        {candles?.volume_unit ? ` (${candles.volume_unit})` : ""}.
      </p>
      {error ? <Warning>{error}</Warning> : null}
      {drawingError ? <Warning>Drawings: {drawingError}</Warning> : null}
      <Notices title="Data notices for this chart" items={notices} open />
      {loading ? (
        <p className="text-[12px] text-muted" role="status">
          Loading the stored scan and candles.
        </p>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="panel h-[560px] overflow-hidden" aria-label="Price chart">
          {loading ? (
            <div className="p-4">
              <Skeleton rows={8} />
            </div>
          ) : series.prepared.ok && series.prepared.candles.length > 0 ? (
            <CandleChart
              candles={series.prepared.candles}
              zones={zones}
              drawings={drawings}
              planLines={showPlans ? planOverlay.lines : []}
              showZones
              showVolume={Boolean(showVolume)}
              selectedZoneId={selectedZoneId}
              selectedDrawingId={selectedDrawingId}
              onSelectZone={setSelectedZoneId}
              onSelectDrawing={setSelectedDrawingId}
              onChangeDrawing={(next) => {
                setDrawings((current) => current.map((row) => (row.drawingId === next.drawingId ? next : row)));
                if (next.persistence !== "PLATFORM_DB") return;
                void (async () => {
                  const patched = await app.request<Record<string, unknown>>(`/api/v1/drawings/${encodeURIComponent(next.drawingId)}`, {
                    method: "PATCH",
                    body: { geometry: { type: next.kind, points: next.points, text: next.text } },
                  });
                  if (!patched.ok) setDrawingError(patched.error.message);
                })();
              }}
              onController={setController}
            />
          ) : series.prepared.ok === false ? (
            <div className="p-4">
              <EmptyState title="Invalid candle series" reason="The series has invalid, duplicate, or out-of-order rows. Rows were not dropped to force a draw." />
            </div>
          ) : (
            <div className="p-4">
              <EmptyState title="No candles at this as-of" reason="The candle route returned no drawable rows. Missing sessions were not filled." />
            </div>
          )}
        </div>
        <aside className="space-y-3 text-[12px]">
          <section className="panel space-y-1 px-3.5 py-3" data-testid="evidence-status">
            <h2 className="mb-1.5 text-[13px] font-semibold">Evidence status</h2>
            {loading ? <p>Loading. No evidence state is assumed yet.</p> : null}
            {evidence.map((row) => (
              <p key={row.source} data-evidence={row.source} data-state={row.state} className="flex gap-2">
                <EvidenceState state={row.state} />
                <span className="min-w-0">
                  <span className="font-medium">{row.source}.</span> <span className="text-muted">{row.detail}</span>
                </span>
              </p>
            ))}
          </section>
          <section className="panel space-y-1.5 px-3.5 py-3">
            <h2 className="text-[13px] font-semibold">Engine zones</h2>
            {zones.length === 0 ? <p className="text-muted">No stored zone with numeric bounds for the visible timeframes. Unknown geometry stays off the chart.</p> : null}
            <ul className="divide-y divide-line">
              {zones.map((zone) => (
                <li key={`${zone.timeframe}:${zone.engineId}`}>
                  <button
                    type="button"
                    aria-pressed={selectedZoneId === zone.engineId}
                    className={`flex w-full items-center justify-between gap-2 py-1.5 text-left ${selectedZoneId === zone.engineId ? "text-[var(--gtf-accent)]" : ""}`}
                    onClick={() => setSelectedZoneId(zone.engineId)}
                  >
                    <span className="min-w-0 truncate">
                      <span className="font-medium">
                        {zone.timeframe} {zone.side}
                      </span>{" "}
                      <span className="code text-muted" title={zone.engineId}>
                        {zone.engineId}
                      </span>
                    </span>
                    <span className="flex shrink-0 items-center gap-1.5">
                      <span className="tabular text-muted">
                        {zone.proximal} / {zone.distal}
                      </span>
                      <StatusBadge code={zone.overlayStatus} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {zones.length ? <p className="text-[11px] text-muted">Proximal / distal. Engine geometry is read-only and not draggable.</p> : null}
            {selectedZone ? <ZoneDetail zone={selectedZone} /> : null}
          </section>
          <section className="panel space-y-1 px-3.5 py-3" data-testid="plan-overlay">
            <h2 className="text-[13px] font-semibold">Plan overlay (FR-4.9)</h2>
            <p className="text-muted">Plan lines are recorded plan levels, labelled PLAN. They are not orders and are not recalculated here.</p>
            {planOverlay.lines.length === 0 && planOverlay.notes.length === 0 ? <p>No plan record for this symbol and scan.</p> : null}
            {planOverlay.lines.map((line) => (
              <p key={`${line.planId}-${line.kind}`} className="flex justify-between gap-2">
                <span>{line.label}</span>
                <span className="tabular">{line.price}</span>
              </p>
            ))}
            {planOverlay.notes.map((note) => (
              <p key={`${note.planId}-note`}>
                {note.planId}: {note.reason}
              </p>
            ))}
            {planRecords.length ? (
              <Button size="sm" type="button" onClick={() => app.navigate("plans", { plan: String(planRecords[0]?.plan_id ?? "") })}>
                Open trade plan
              </Button>
            ) : null}
          </section>
        </aside>
      </div>

      <Panel
        title="Stored qualification (G0–G8)"
        subtitle="Gate outcomes as stored by the research pipeline. The status is the most restrictive gate. Nothing here is an order."
      >
        <Qualification
          candidates={candidates}
          onPlan={(zone) => app.navigate("plans", { scan, symbol, zone, fixtures: view.fixtures ? "1" : null })}
        />
      </Panel>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel title="Stored explanation" subtitle="Deterministic text from the stored scan.">
          <ul className="space-y-1 text-[12px] leading-[1.55]">
            {(explain || ["NOT_IN_SCAN"]).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Panel>
        <Panel title="Data quality">
          <KeyValue
            rows={[
              ["Research use", researchUse ? <span className="code">{researchUse}</span> : "unavailable"],
              ["Identity", quality?.identity_status || "unavailable"],
              ["Volume source", candles?.volume_source || "unavailable"],
              ["Available from", candles?.available_from || "unavailable"],
              ["Available to", candles?.available_to || "unavailable"],
            ]}
          />
          <p className="text-[11.5px] text-muted">authorises_order remains false. data_ready remains false on this path.</p>
        </Panel>
        <Panel title="Annotations" subtitle="User drawings persist in the platform database (FR-4.3). They are not eligibility inputs.">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => {
                const last = series.prepared.ok ? series.prepared.candles.at(-1) : undefined;
                if (!last) return;
                void (async () => {
                  const created = await app.request<Record<string, unknown>>("/api/v1/drawings", {
                    method: "POST",
                    idempotencyKey: newKey(),
                    body: {
                      symbol,
                      timeframe,
                      as_of: resolvedAsOf || asOfFromQuery,
                      geometry: { type: "horizontal", points: [{ time: last.time, price: last.close }], text: "owner mark" },
                    },
                  });
                  if (!created.ok) {
                    setDrawingError(created.error.message);
                    return;
                  }
                  const row = drawingFromApi(created.envelope.data, { symbol, timeframe });
                  if (row) setDrawings((current) => [...current, row]);
                })();
              }}
            >
              Save a horizontal mark
            </Button>
            {selectedDrawingId ? (
              <Button
                type="button"
                size="sm"
                variant="danger"
                onClick={() => {
                  void (async () => {
                    const removed = await app.request(`/api/v1/drawings/${encodeURIComponent(selectedDrawingId)}`, { method: "DELETE", idempotencyKey: newKey() });
                    if (!removed.ok) {
                      setDrawingError(removed.error.message);
                      return;
                    }
                    setDrawings((current) => current.filter((row) => row.drawingId !== selectedDrawingId));
                    setSelectedDrawingId(null);
                  })();
                }}
              >
                Delete selected drawing
              </Button>
            ) : null}
          </div>
          <ul className="space-y-1 text-[12px]">
            {drawings.length === 0 ? <li className="text-muted">No drawings for this symbol and timeframe.</li> : null}
            {drawings.map((row) => (
              <li key={row.drawingId}>
                <button type="button" className={`underline-offset-2 hover:underline ${selectedDrawingId === row.drawingId ? "font-semibold text-[var(--gtf-drawing)]" : ""}`} onClick={() => setSelectedDrawingId(row.drawingId)}>
                  {row.kind} @ {row.points[0]?.price ?? "n/a"} ({row.persistence})
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </Page>
  );
}

function EvidenceState({ state }: { state: string }) {
  const tone =
    state === "AVAILABLE"
      ? "text-ink-2 border-line-strong"
      : state === "MISSING" || state === "UNAVAILABLE"
        ? "text-[var(--gtf-fail)] border-[var(--gtf-fail)]/50"
        : "text-[var(--gtf-manual)] border-[var(--gtf-manual)]/50 border-dashed";
  return <span className={`code inline-flex h-[18px] shrink-0 items-center rounded-[3px] border px-1 text-[10px] font-semibold ${tone}`}>{state}</span>;
}

function NoScan(props: { symbol: string }) {
  const app = useAppState();
  const scans = useApi<ScanListData>(props.symbol ? "/api/v1/scans" : null, { limit: 10, include_fixtures: true });
  const rows = dataOf(scans)?.scans ?? [];
  return (
    <Page eyebrow="Research" title="Stock Analysis" description="Monthly, weekly, and daily candles from a stored scan.">
      <EmptyState
        title="No stored symbol"
        reason="Open a symbol from a stored scan (FR-4.5). Standalone chart inspection without a scan is not authorised without an owner decision (OD-P2-1)."
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <Button type="button" onClick={() => app.navigate("scanner")}>
              Open the scanner
            </Button>
            <Button type="button" onClick={() => app.navigate("history")}>
              Scan history
            </Button>
          </div>
        }
      />
      {props.symbol ? (
        <Panel title={`Choose a stored scan for ${props.symbol}`} subtitle="The chart is drawn only from a stored scan. If the symbol is not in the scan you choose, the page says so; nothing is recomputed.">
          {scans.state === "loading" ? <Skeleton rows={3} /> : null}
          {scans.state === "ready" && rows.length === 0 ? <p className="text-[12px] text-muted">No stored scan exists yet.</p> : null}
          <ul className="divide-y divide-line">
            {rows.map((row) => (
              <li key={row.scan_key} className="flex flex-wrap items-center justify-between gap-2 py-2 text-[12.5px]">
                <span>
                  <span className="code">{row.scan_key}</span>
                  <span className="text-muted">
                    {" "}
                    · as of {row.as_of?.slice(0, 10) ?? "?"} · {row.completeness ?? "?"}
                  </span>{" "}
                  {row.fixture ? <ProvenanceBadge kind="FIXTURE" /> : null}
                </span>
                <Button size="sm" type="button" onClick={() => app.navigate("analysis", { symbol: props.symbol, scan: row.scan_key, fixtures: row.fixture ? "1" : null })}>
                  Open {props.symbol} in this scan
                </Button>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </Page>
  );
}

function ZoneDetail(props: { zone: ZoneView }) {
  const zone = props.zone;
  return (
    <div className="mt-2 rounded-[4px] border border-line bg-surface-2 p-2.5">
      <KeyValue
        rows={[
          ["Zone", <span className="code">{zone.engineId}</span>],
          ["Symbol · TF · side", `${zone.symbol} · ${zone.timeframe} · ${zone.side}`],
          ["Proximal", <span className="tabular">{zone.proximal}</span>],
          ["Distal", <span className="tabular">{zone.distal}</span>],
          ["Created", zone.createdTime || <Unavailable />],
          ["Overlay", zone.overlayStatus],
          ...(zone.engineStatus ? ([["Engine", zone.engineStatus]] as Array<[string, ReactNode]>) : []),
          ...(zone.disposition ? ([["Disposition", zone.disposition]] as Array<[string, ReactNode]>) : []),
          ...(typeof zone.testCount === "number" ? ([["Test count", String(zone.testCount)]] as Array<[string, ReactNode]>) : []),
        ]}
      />
      <p className="mt-1 text-[11px] text-muted">Not an order. Fresh styling is not qualification.</p>
    </div>
  );
}

function Qualification(props: { candidates: Array<Record<string, unknown>>; onPlan: (zone: string) => void }) {
  if (props.candidates.length === 0) {
    return <p className="text-[12.5px] text-muted">No stored candidate. Qualification unavailable. Nothing here is a pass.</p>;
  }
  return (
    <div className="space-y-4">
      {props.candidates.map((candidate, index) => {
        const status = String(candidate.status || candidate.candidate_status || "UNAVAILABLE");
        const gates = Array.isArray(candidate.gates) ? (candidate.gates as Array<Record<string, unknown>>) : [];
        const zone = String(candidate.zone_id || (candidate.zone as { zone_id?: unknown } | undefined)?.zone_id || "");
        return (
          <div key={index}>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="flex flex-wrap items-center gap-2 text-[12.5px]">
                <span className="eyebrow">Candidate</span>
                <span className="code">{zone || "zone unavailable"}</span>
                <StatusBadge code={status} />
                <span className="sr-only">Status {status}.</span>
                <span className="text-muted">This is not an order.</span>
              </p>
              {zone ? (
                <Button size="sm" type="button" onClick={() => props.onPlan(zone)}>
                  Draft a plan from this candidate
                </Button>
              ) : null}
            </div>
            {gates.length ? (
              <div className="overflow-auto rounded-[4px] border border-line">
                <table className="gtf-table w-full border-collapse text-[12px]">
                  <caption className="sr-only">Gate outcomes for {zone}</caption>
                  <thead className="bg-surface-2">
                    <tr>
                      <th scope="col" className="w-14 border-b border-line px-2.5 py-1.5 text-left">Gate</th>
                      <th scope="col" className="w-36 border-b border-line px-2.5 py-1.5 text-left">Outcome</th>
                      <th scope="col" className="border-b border-line px-2.5 py-1.5 text-left">Reasons</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gates.map((gate) => (
                      <tr key={String(gate.gate)}>
                        <td className="border-b border-line px-2.5 py-1.5 align-top font-semibold">{String(gate.gate)}</td>
                        <td className="border-b border-line px-2.5 py-1.5 align-top">
                          <StatusBadge code={String(gate.outcome)} />
                        </td>
                        <td className="border-b border-line px-2.5 py-1.5 align-top leading-[1.5] text-ink-2">
                          {gate.title ? <span className="font-medium text-ink">{String(gate.title)}. </span> : null}
                          {Array.isArray(gate.reasons) ? (gate.reasons as unknown[]).map(String).join("; ") : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-[12px] text-muted">No gate rows stored for this candidate.</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
