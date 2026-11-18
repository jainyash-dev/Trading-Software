import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button, Checkbox, EmptyState, SelectInput, Skeleton, StatusBadge, TextInput, Unavailable } from "../../design/components";
import { connectionLabel } from "../../services/connection";
import { isoDate, jobPollInterval, newIdempotencyKey, stable } from "../../services/idempotency";
import { useAppState } from "../../state/store";
import type {
  ApiErrorBody,
  CandlePayload,
  DatasetRow,
  JobData,
  ResearchEnvelope,
  ResearchSymbol,
  ScanConfig,
  ScanListData,
  ScanSummary,
  ScanSymbolsData,
  SymbolBundle,
  Watchlist,
} from "../../types/contracts";
import { InstrumentFinder } from "../shared/InstrumentFinder";
import { Completeness, ErrorLine, Fact, FactGrid, JobState, Section, Value, Warning } from "../shared/ui";
import {
  applyConfigParameters,
  candidateStatusOf,
  configParameters,
  fieldText,
  filterSymbols,
  forbiddenParameterPaths,
  isActiveJob,
  isTerminalJob,
  listedTimeframes,
  progressLabel,
  qualityCodes,
  SCAN_MODES,
  scanOutcome,
  scanRequestBody,
  symbolStatusOf,
  textList,
  TRADE_TYPES,
  type ResultFilter,
  type ScanDraft,
  type ScanOutcome,
} from "./model";
import { readViewQuery } from "../../navigation/query";
import { readPendingScan, writePendingScan, type PendingScan } from "./storage";

export function ScannerPage() {
  const app = useAppState();
  const request = app.request;
  const reportFailure = app.reportFailure;
  const noteFixture = app.noteFixture;
  const navigate = app.navigate;
  const query = new URLSearchParams(app.queryString);
  const requestedScan = query.get("scan");
  const [draft, setDraft] = useState<ScanDraft>(() => ({
    mode: "MANUAL",
    tradeType: "MIT",
    universeMode: "SUPPORTED",
    symbols: [],
    asOf: isoDate(app.health?.last_successful_ingest_date) ?? "",
    datasetId: "",
    risk: null,
  }));
  const [datasets, setDatasets] = useState<DatasetRow[] | null>(null);
  const [configs, setConfigs] = useState<ScanConfig[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [setupError, setSetupError] = useState<ApiErrorBody | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [ignored, setIgnored] = useState<string[]>([]);
  const [configId, setConfigId] = useState("");
  const [configName, setConfigName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [httpStatus, setHttpStatus] = useState<number | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [job, setJob] = useState<JobData | null>(null);
  const [trackedJobId, setTrackedJobId] = useState<string | null>(null);
  const [jobError, setJobError] = useState<ApiErrorBody | null>(null);
  const [cancelNote, setCancelNote] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [restoreNote, setRestoreNote] = useState(false);
  const [resume, setResume] = useState<PendingScan | null>(null);
  const [includeFixtures, setIncludeFixtures] = useState(query.get("fixtures") === "1");
  const [history, setHistory] = useState<ScanSummary[]>([]);
  const [historyCursor, setHistoryCursor] = useState<string | null>(null);
  const [historyTick, setHistoryTick] = useState(0);
  const [historyState, setHistoryState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [historyError, setHistoryError] = useState<ApiErrorBody | null>(null);
  const [envelope, setEnvelope] = useState<ResearchEnvelope | null>(null);
  const [envelopeFixture, setEnvelopeFixture] = useState(false);
  const [symbols, setSymbols] = useState<ResearchSymbol[]>([]);
  const [detailError, setDetailError] = useState<ApiErrorBody | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [bundle, setBundle] = useState<SymbolBundle | null>(null);
  const [bundleFixture, setBundleFixture] = useState(false);
  const [bundleError, setBundleError] = useState<ApiErrorBody | null>(null);
  const [candles, setCandles] = useState<CandlePayload | null>(null);
  const [candleFixture, setCandleFixture] = useState(false);
  const [candleError, setCandleError] = useState<ApiErrorBody | null>(null);
  const [candleTf, setCandleTf] = useState("D");
  const [showAllCandles, setShowAllCandles] = useState(false);
  const [filters, setFilters] = useState<ResultFilter>({
    symbol: query.get("symbol") ?? "",
    status: "",
    timeframe: "",
    quality: "",
  });
  const lock = useRef(false);
  const detailSeq = useRef(0);
  const evidenceSeq = useRef(0);
  const connected = app.connection === "connected";

  useEffect(() => {
    const pending = readPendingScan();
    if (pending?.jobId) {
      setTrackedJobId(pending.jobId);
      setRestoreNote(true);
      setAccepted(true);
    } else if (pending) setResume(pending);
  }, []);

  useEffect(() => {
    const view = readViewQuery(app.queryString);
    if (view.fixtures) setIncludeFixtures(true);
    if (view.rejected.includes("symbol")) setFilters((current) => ({ ...current, symbol: "" }));
    else if (view.symbol) {
      setFilters((current) => ({ ...current, symbol: view.symbol }));
      setSelectedSymbol(view.symbol);
    }
    if (new URLSearchParams(app.queryString).get("panel") === "history") document.getElementById("scan-history")?.scrollIntoView();
  }, [app.queryString]);

  useEffect(() => {
    if (!connected) return;
    const controller = new AbortController();
    let active = true;
    void (async () => {
      const [datasetResult, configResult, watchResult] = await Promise.all([
        request<{ datasets?: DatasetRow[] }>("/api/v1/datasets", { signal: controller.signal }),
        request<{ scan_configs?: ScanConfig[] }>("/api/v1/scan-configs", { signal: controller.signal }),
        request<{ watchlists?: Watchlist[] }>("/api/v1/watchlists", { signal: controller.signal }),
      ]);
      if (!active) return;
      if (!datasetResult.ok) {
        reportFailure(datasetResult);
        setSetupError(datasetResult.error);
        setDatasets([]);
      } else {
        const rows = datasetResult.envelope.data.datasets ?? [];
        setDatasets(rows);
        noteFixture("scanner-datasets", datasetResult.envelope.meta.fixture || rows.some((row) => row.fixture === true));
        setDraft((current) => (current.datasetId || !rows[0]?.dataset_id ? current : { ...current, datasetId: rows[0].dataset_id ?? "" }));
      }
      if (configResult.ok) setConfigs(configResult.envelope.data.scan_configs ?? []);
      else setSetupError(configResult.error);
      if (watchResult.ok) setWatchlists(watchResult.envelope.data.watchlists ?? []);
    })();
    return () => {
      active = false;
      controller.abort();
    };
  }, [connected, app.revision, request, reportFailure, noteFixture]);

  useEffect(() => {
    if (!connected) return;
    const controller = new AbortController();
    let active = true;
    setHistoryState("loading");
    void request<ScanListData>("/api/v1/scans", {
      signal: controller.signal,
      query: { limit: 50, ...(includeFixtures ? { include_fixtures: true } : {}) },
    }).then((result) => {
      if (!active) return;
      if (!result.ok) {
        reportFailure(result);
        setHistoryError(result.error);
        setHistoryState("error");
        return;
      }
      setHistory(result.envelope.data.scans ?? []);
      setHistoryCursor(result.envelope.data.next_cursor ?? null);
      setHistoryState("ready");
      noteFixture("scanner-history", result.envelope.meta.fixture);
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [connected, includeFixtures, app.revision, historyTick, request, reportFailure, noteFixture]);

  useEffect(() => {
    if (job && isTerminalJob(job.state)) setHistoryTick((value) => value + 1);
  }, [job?.job_id, job?.state]);

  useEffect(() => {
    if (!trackedJobId || !connected) return;
    const controller = new AbortController();
    let stopped = false;
    let timer = 0;
    const tick = async () => {
      try {
        const result = await request<JobData>(`/api/v1/jobs/${encodeURIComponent(trackedJobId)}`, { signal: controller.signal });
        if (stopped) return;
        if (!result.ok) {
          reportFailure(result);
          setJobError(result.error);
          return;
        }
        setJob(result.envelope.data);
        setJobError(null);
        if (!isTerminalJob(result.envelope.data.state)) {
          timer = window.setTimeout(() => void tick(), jobPollInterval());
          return;
        }
        const ref = result.envelope.data.result_ref;
        if (ref && new URLSearchParams(window.location.hash.split("?")[1] ?? "").get("scan") !== ref) {
          navigate("scanner", { scan: ref, ...(includeFixtures ? { fixtures: "1" } : {}) });
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (!stopped) setJobError({ code: "DISCONNECTED", message: "Local API is not reachable", details: {} });
      }
    };
    void tick();
    return () => {
      stopped = true;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [trackedJobId, connected, includeFixtures, request, reportFailure, navigate]);

  useEffect(() => {
    if (!requestedScan || !connected) return;
    const controller = new AbortController();
    const seq = ++detailSeq.current;
    setDetailLoading(true);
    setDetailError(null);
    const queryFlags = includeFixtures ? { include_fixtures: true } : undefined;
    void (async () => {
      const stored = await request<ResearchEnvelope>(`/api/v1/scans/${encodeURIComponent(requestedScan)}`, {
        query: queryFlags,
        signal: controller.signal,
      });
      if (detailSeq.current !== seq) return;
      if (!stored.ok) {
        reportFailure(stored);
        setEnvelope(null);
        setSymbols([]);
        setDetailError(stored.error);
        setDetailLoading(false);
        return;
      }
      const listed = await request<ScanSymbolsData>(`/api/v1/scans/${encodeURIComponent(requestedScan)}/symbols`, {
        query: queryFlags,
        signal: controller.signal,
      });
      if (detailSeq.current !== seq) return;
      setEnvelope(stored.envelope.data);
      setEnvelopeFixture(stored.envelope.meta.fixture);
      noteFixture("scanner-detail", stored.envelope.meta.fixture);
      if (listed.ok) {
        setSymbols(listed.envelope.data.symbols ?? []);
        noteFixture("scanner-detail", stored.envelope.meta.fixture || listed.envelope.meta.fixture);
      } else {
        setSymbols(stored.envelope.data.symbols ?? []);
        setDetailError(listed.error);
      }
      setDetailLoading(false);
    })();
    return () => controller.abort();
  }, [requestedScan, connected, includeFixtures, request, reportFailure, noteFixture]);

  useEffect(() => {
    if (!selectedSymbol || !requestedScan || !envelope || !connected) return;
    const controller = new AbortController();
    const seq = ++evidenceSeq.current;
    setBundle(null);
    setCandles(null);
    setBundleError(null);
    setCandleError(null);
    const flags = includeFixtures ? { include_fixtures: true } : {};
    void (async () => {
      const bundleResult = await request<SymbolBundle>(`/api/v1/symbols/${encodeURIComponent(selectedSymbol)}/bundle`, {
        signal: controller.signal,
        query: {
          scan_key: requestedScan,
          ...flags,
          ...(envelope.dataset_id ? { dataset_id: envelope.dataset_id } : {}),
          ...(envelope.as_of ? { as_of: envelope.as_of } : {}),
          ...(envelope.trade_type ? { trade_type: envelope.trade_type } : {}),
        },
      });
      if (evidenceSeq.current !== seq) return;
      if (!bundleResult.ok) {
        reportFailure(bundleResult);
        setBundleError(bundleResult.error);
      } else {
        setBundle(bundleResult.envelope.data);
        setBundleFixture(bundleResult.envelope.meta.fixture);
        noteFixture("scanner-bundle", bundleResult.envelope.meta.fixture);
      }
      if (!envelope.dataset_id || !envelope.as_of) {
        setCandleError({ code: "NOT_SUPPLIED", message: "dataset_id and as_of were not both present on the stored scan", details: {} });
        return;
      }
      const candleResult = await request<CandlePayload>("/api/v1/candles", {
        signal: controller.signal,
        query: { symbol: selectedSymbol, timeframe: candleTf, as_of: envelope.as_of, dataset_id: envelope.dataset_id },
      });
      if (evidenceSeq.current !== seq) return;
      if (!candleResult.ok) {
        reportFailure(candleResult);
        setCandleError(candleResult.error);
        return;
      }
      setCandles(candleResult.envelope.data);
      setCandleFixture(candleResult.envelope.meta.fixture);
      noteFixture("scanner-candles", candleResult.envelope.meta.fixture);
    })();
    return () => controller.abort();
  }, [selectedSymbol, requestedScan, envelope, candleTf, includeFixtures, connected, request, reportFailure, noteFixture]);

  async function submit(body: Record<string, unknown>, key: string) {
    if (lock.current) return;
    lock.current = true;
    setSubmitting(true);
    setFormError(null);
    writePendingScan({ idempotencyKey: key, body });
    const result = await request<JobData>("/api/v1/scans", { method: "POST", body, idempotencyKey: key });
    lock.current = false;
    setSubmitting(false);
    if (!result.ok) {
      reportFailure(result);
      setFormError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    setHttpStatus(result.status);
    setAccepted(true);
    setJob(result.envelope.data);
    setTrackedJobId(result.envelope.data.job_id);
    setResume(null);
    writePendingScan({ idempotencyKey: key, body, jobId: result.envelope.data.job_id });
    noteFixture("scanner-job", result.envelope.meta.fixture);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (lock.current || (job && isActiveJob(job.state))) return;
    const built = scanRequestBody(draft);
    if (!built.ok) {
      setFormError(built.message);
      return;
    }
    const pending = readPendingScan();
    if (pending?.jobId && stable(pending.body) === stable(built.body) && job && isActiveJob(job.state)) return;
    void submit(built.body, newIdempotencyKey());
  }

  async function cancel() {
    if (!trackedJobId || cancelling) return;
    setCancelling(true);
    const result = await request<JobData>(`/api/v1/scans/${encodeURIComponent(trackedJobId)}/cancel`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
    setCancelling(false);
    if (!result.ok) {
      reportFailure(result);
      setJobError(result.error);
      return;
    }
    setJob(result.envelope.data);
    setCancelNote(!isTerminalJob(result.envelope.data.state));
  }

  async function saveConfig() {
    const name = configName.trim();
    if (!name) {
      setFormError("name is required");
      return;
    }
    const parameters = configParameters(draft);
    const blocked = forbiddenParameterPaths(parameters);
    if (blocked.length) {
      setFormError(`Not saved. These parameters are not applied: ${blocked.join(", ")}`);
      return;
    }
    const result = await request<ScanConfig>("/api/v1/scan-configs", {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
      body: { name, parameters },
    });
    if (!result.ok) {
      reportFailure(result);
      setFormError(`${result.error.code}: ${result.error.message}`);
      return;
    }
    setConfigs((current) => [...current.filter((item) => item.config_id !== result.envelope.data.config_id), result.envelope.data]);
    setConfigId(result.envelope.data.config_id);
    setConfigName("");
  }

  async function loadMore() {
    if (!historyCursor) return;
    const result = await request<ScanListData>("/api/v1/scans", {
      query: { limit: 50, cursor: historyCursor, ...(includeFixtures ? { include_fixtures: true } : {}) },
    });
    if (!result.ok) {
      reportFailure(result);
      setHistoryError(result.error);
      return;
    }
    setHistory((current) => [...current, ...(result.envelope.data.scans ?? [])]);
    setHistoryCursor(result.envelope.data.next_cursor ?? null);
    noteFixture("scanner-history", result.envelope.meta.fixture);
  }

  const progress = progressLabel(job?.progress);
  const filtered = filterSymbols(symbols, filters);
  const outcome = scanOutcome({
    envelope,
    connected,
    error: detailError,
    currentDatasetIds: datasets === null || datasets.length === 0 ? null : datasets.map((row) => row.dataset_id).filter((id): id is string => typeof id === "string"),
  });
  const acceptedRows = history.filter((row) => row.fixture !== true);
  const fixtureRows = history.filter((row) => row.fixture === true);
  const active = Boolean(job && isActiveJob(job.state));
  const dataReady = app.health?.data_ready;

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-4 px-5 py-4">
      <header className="border-b border-line pb-3">
        <p className="eyebrow">Research</p>
          <h1 className="mt-0.5 text-[19px] font-semibold leading-6 tracking-[-0.01em]">Opportunity Scanner</h1>
        <p className="mt-1 max-w-4xl text-[12.5px] leading-[1.5] text-muted">
          Submits a scan to the stored GTF research pipeline and displays the returned envelope. This screen does not score, rank, recompute gates, or approve a trade.
        </p>
      </header>
      {connected && dataReady === false ? <Warning>data_ready is false. Submitting a scan does not claim DATA_READY.</Warning> : null}
      {!connected ? (
        <EmptyState title={connectionLabel(app.connection)} reason="Scan requests wait for a session. Nothing was submitted from this render." />
      ) : null}
      {setupError ? <ErrorLine error={setupError} onRetry={app.reload} /> : null}

      <div className="grid items-start gap-3 xl:grid-cols-[320px_minmax(0,1fr)]">
        <form className="panel space-y-3 p-3.5" onSubmit={onSubmit}>
          <h2 className="text-[13px] font-semibold">Scan request</h2>
          <p className="text-[12px] text-muted">
            WIT-75 and WIT-125 are sent to the research engine. If the engine returns BLOCKED, that result stays blocked. Rules.max_base_candles cannot be edited here.
          </p>
          <SelectInput
            label="Configuration"
            value={configId}
            onChange={(event) => {
              const id = event.target.value;
              setConfigId(id);
              const config = configs.find((item) => item.config_id === id);
              if (!config) {
                setIgnored([]);
                return;
              }
              const applied = applyConfigParameters(draft, config.parameters);
              setDraft(applied.draft);
              setIgnored(applied.ignored);
            }}
          >
            <option value="">No saved configuration</option>
            {configs.map((config) => (
              <option key={config.config_id} value={config.config_id}>
                {config.name}
              </option>
            ))}
          </SelectInput>
          {configId ? (
            <div className="text-[12px]">
              <p className="font-medium">Stored parameters</p>
              <ParameterList parameters={configs.find((item) => item.config_id === configId)?.parameters ?? {}} ignored={ignored} />
            </div>
          ) : null}
          <SelectInput label="Mode" value={draft.mode} onChange={(event) => setDraft({ ...draft, mode: event.target.value })}>
            {SCAN_MODES.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </SelectInput>
          <SelectInput label="Trade type" value={draft.tradeType} onChange={(event) => setDraft({ ...draft, tradeType: event.target.value })}>
            {TRADE_TYPES.map((tradeType) => (
              <option key={tradeType} value={tradeType}>
                {tradeType}
              </option>
            ))}
          </SelectInput>
          <TextInput label="As of" type="date" value={draft.asOf} onChange={(event) => setDraft({ ...draft, asOf: event.target.value })} />
          <SelectInput label="Dataset" value={draft.datasetId} onChange={(event) => setDraft({ ...draft, datasetId: event.target.value })}>
            <option value="">Select a dataset</option>
            {datasets?.map((row) => (
              <option key={row.dataset_id} value={row.dataset_id}>
                {row.dataset_id}
                {row.fixture ? " fixture" : ""}
              </option>
            ))}
          </SelectInput>
          {datasets?.length === 0 && connected ? <p className="text-[12px]">No dataset is configured.</p> : null}
          <SelectInput
            label="Universe"
            value={draft.universeMode}
            onChange={(event) => setDraft({ ...draft, universeMode: event.target.value === "LIST" ? "LIST" : "SUPPORTED", symbols: event.target.value === "LIST" ? draft.symbols : [] })}
          >
            <option value="SUPPORTED">SUPPORTED</option>
            <option value="LIST">Symbol list</option>
          </SelectInput>
          {draft.universeMode === "SUPPORTED" ? (
            <p className="text-[12px] text-muted">The request universe is SUPPORTED. This form does not certify it.</p>
          ) : (
            <div className="space-y-2">
              <p className="text-[12px] text-muted">This scan will request an ad-hoc symbol list.</p>
              <SelectInput
                label="Copy a watchlist"
                value=""
                onChange={(event) => {
                  const list = watchlists.find((item) => item.watchlist_id === event.target.value);
                  if (!list) return;
                  setDraft({ ...draft, universeMode: "LIST", symbols: [...list.symbols] });
                }}
              >
                <option value="">Choose a watchlist</option>
                {watchlists.map((list) => (
                  <option key={list.watchlist_id} value={list.watchlist_id}>
                    {list.name}
                  </option>
                ))}
              </SelectInput>
              <InstrumentFinder
                label="Add a returned instrument"
                onSelect={(instrument) =>
                  setDraft((current) =>
                    current.symbols.includes(instrument.symbol) ? current : { ...current, symbols: [...current.symbols, instrument.symbol] },
                  )
                }
              />
              <ul className="text-[12px]">
                {draft.symbols.map((symbol) => (
                  <li key={symbol} className="flex items-center justify-between gap-2 border-b border-line py-1">
                    <span>{symbol}</span>
                    <Button type="button" onClick={() => setDraft({ ...draft, symbols: draft.symbols.filter((item) => item !== symbol) })}>
                      Remove {symbol}
                    </Button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Checkbox
            label="Include risk inputs"
            checked={draft.risk !== null}
            onChange={(checked) => setDraft({ ...draft, risk: checked ? { kind: "pct", capital: "", rpt: "", stage: "" } : null })}
          />
          {draft.risk ? (
            <div className="space-y-2">
              <TextInput label="Capital" value={draft.risk.capital} onChange={(event) => setDraft({ ...draft, risk: { ...draft.risk!, capital: event.target.value } })} />
              <SelectInput label="Risk field" value={draft.risk.kind} onChange={(event) => setDraft({ ...draft, risk: { ...draft.risk!, kind: event.target.value === "amount" ? "amount" : "pct" } })}>
                <option value="pct">rpt_pct</option>
                <option value="amount">rpt_amount</option>
              </SelectInput>
              <TextInput label={draft.risk.kind === "pct" ? "rpt_pct" : "rpt_amount"} value={draft.risk.rpt} onChange={(event) => setDraft({ ...draft, risk: { ...draft.risk!, rpt: event.target.value } })} />
              <SelectInput label="Stage" value={draft.risk.stage} onChange={(event) => setDraft({ ...draft, risk: { ...draft.risk!, stage: event.target.value } })}>
                <option value="">Not supplied</option>
                <option value="LEARNING">LEARNING</option>
                <option value="INTERMEDIATE">INTERMEDIATE</option>
                <option value="PROFESSIONAL">PROFESSIONAL</option>
              </SelectInput>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <TextInput label="Configuration name" value={configName} onChange={(event) => setConfigName(event.target.value)} />
            <Button type="button" onClick={() => void saveConfig()}>
              Save configuration
            </Button>
          </div>
          {formError ? <p className="text-[12px]">{formError}</p> : null}
          {resume ? (
            <Warning>
              A scan submission was interrupted before a job id was stored. Resume reuses the same idempotency key.
              <Button
                type="button"
                className="ml-2"
                onClick={() => void submit(resume.body, resume.idempotencyKey)}
              >
                Resume submission
              </Button>
            </Warning>
          ) : null}
          <Button type="submit" variant="primary" disabled={!connected || submitting || active}>
            {submitting ? "Submitting" : active ? "Scan in progress" : "Run scan"}
          </Button>
        </form>

        <div className="space-y-3">
          <Section title="Job">
            {restoreNote ? <p className="text-[12px]">Restored the stored job. The scan was not submitted again.</p> : null}
            {!job && !jobError ? <p className="text-[12px] text-muted">No job is being monitored.</p> : null}
            {jobError ? <ErrorLine error={jobError} /> : null}
            {job ? (
              <div aria-live="polite" className="space-y-2">
                <FactGrid>
                  <Fact label="Job">{job.job_id}</Fact>
                  <Fact label="HTTP status">{httpStatus ?? <Unavailable />}</Fact>
                  <Fact label="Job state">
                    <JobState state={job.state} />
                  </Fact>
                  <Fact label="Completeness">
                    <Completeness value={job.completeness} />
                  </Fact>
                  <Fact label="Result">{job.result_ref || <Unavailable />}</Fact>
                  <Fact label="Progress">{progress ?? <Unavailable />}</Fact>
                </FactGrid>
                {accepted && httpStatus === 202 && !isTerminalJob(job.state) ? (
                  <Warning>Accepted (HTTP 202). Job state {job.state}. This is not a completed scan.</Warning>
                ) : null}
                {job.state === "SUCCEEDED_PARTIAL" ? <Warning>SUCCEEDED_PARTIAL is a finished job and a partial scan.</Warning> : null}
                {job.state === "FAILED" || job.state === "INTERRUPTED" ? (
                  <Warning>
                    A {job.state} scan is not a scan with zero candidates. {job.state}
                    {job.error?.code ? ` · ${job.error.code}` : ""}
                    {job.error?.message ? ` · ${job.error.message}` : ""}
                  </Warning>
                ) : null}
                {job.state === "SKIPPED_HOLIDAY" || job.state === "SKIPPED_UNRESOLVED_CALENDAR" ? (
                  <p className="text-[12px]">
                    {job.state}
                    {job.error?.message ? ` · ${job.error.message}` : ""}
                  </p>
                ) : null}
                {cancelNote && !isTerminalJob(job.state) ? (
                  <Warning>Cancellation requested. The job state is still {job.state}.</Warning>
                ) : null}
                {isActiveJob(job.state) ? (
                  <Button type="button" onClick={() => void cancel()} disabled={cancelling}>
                    {cancelling ? "Requesting cancellation" : "Cancel job"}
                  </Button>
                ) : null}
              </div>
            ) : null}
          </Section>

          <Section
            id="scan-history"
            title="Scan history"
            action={
              <Button type="button" onClick={() => setIncludeFixtures((value) => !value)}>
                {includeFixtures ? "Hide fixture scans" : "Show fixture scans"}
              </Button>
            }
          >
            {historyState === "loading" ? <Skeleton rows={3} /> : null}
            {historyError ? <ErrorLine error={historyError} /> : null}
            {historyState === "ready" && acceptedRows.length === 0 ? (
              <EmptyState title="No accepted-data scans" reason="Fixture rows stay out of this table." />
            ) : null}
            {acceptedRows.length > 0 ? (
              <HistoryTable rows={acceptedRows} job={job} onOpen={(scanKey) => app.navigate("scanner", { scan: scanKey })} />
            ) : null}
            {includeFixtures ? (
              <div className="space-y-2">
                <p className="text-[12px] font-semibold">FIXTURE_NOT_MARKET_DATA</p>
                {fixtureRows.length === 0 ? (
                  <EmptyState title="No fixture scans" reason="include_fixtures was requested and no fixture row was returned." />
                ) : (
                  <HistoryTable rows={fixtureRows} job={job} onOpen={(scanKey) => app.navigate("scanner", { scan: scanKey, fixtures: "1" })} />
                )}
              </div>
            ) : null}
            {historyCursor ? (
              <Button type="button" onClick={() => void loadMore()}>
                Load more
              </Button>
            ) : null}
          </Section>
        </div>
      </div>

      <Section title="Stored research">
        {!requestedScan ? <EmptyState title="No scan is open" reason="Inspect a history row or wait until a job returns result_ref." /> : null}
        {detailLoading ? <Skeleton rows={4} /> : null}
        {detailError ? (
          <ErrorLine error={detailError} />
        ) : null}
        {!envelope && requestedScan ? <ScanOutcomePanel outcome={outcome} /> : null}
        {detailError?.code === "NOT_FOUND" && !includeFixtures ? (
          <p className="text-[12px]">Scan was not found among accepted-data scans. Fixture scans stay hidden until you show them.</p>
        ) : null}
        {envelope ? (
          <div className="space-y-3">
            {envelopeFixture ? <Warning>FIXTURE_NOT_MARKET_DATA. These rows are not accepted NSE prices.</Warning> : null}
            <FactGrid>
              <Fact label="Schema">
                <Value value={envelope.schema} />
              </Fact>
              <Fact label="Trade type">
                <Value value={envelope.trade_type} />
              </Fact>
              <Fact label="As of">
                <Value value={envelope.as_of} />
              </Fact>
              <Fact label="Invocation">
                <Value value={envelope.invocation} />
              </Fact>
              <Fact label="Dataset">
                <Value value={envelope.dataset_id} />
              </Fact>
              <Fact label="Completeness">
                <Completeness value={envelope.completeness} />
              </Fact>
              <Fact label="full_universe_scan">
                <Value value={envelope.full_universe_scan} />
              </Fact>
              <Fact label="authorises_order">
                <Value value={envelope.authorises_order} />
              </Fact>
              <Fact label="Pipeline">
                <Value value={fieldText(envelope.methodology?.pipeline_version)} />
              </Fact>
              <Fact label="Symbols not opened">
                {(envelope.symbols_not_opened ?? []).length ? envelope.symbols_not_opened?.join(", ") : <Unavailable />}
              </Fact>
            </FactGrid>
            {envelope.completeness === "PARTIAL" ? <Warning>Stored completeness is PARTIAL.</Warning> : null}
            {envelope.completeness === "FAILED" ? <Warning>Stored completeness is FAILED.</Warning> : null}
            <ScanOutcomePanel outcome={outcome} />
            <div className="text-[12px]">
              <p className="font-medium">Limitations</p>
              {(envelope.limitations ?? []).length ? envelope.limitations?.join(", ") : "None returned"}
            </div>
            <p className="text-[11px] text-muted">{typeof envelope.ranking === "string" ? envelope.ranking : "Ranking note unavailable."}</p>
            <div className="flex flex-wrap gap-2">
              <TextInput label="Symbol filter" value={filters.symbol} onChange={(event) => setFilters({ ...filters, symbol: event.target.value })} />
              <SelectInput label="Decision status" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
                <option value="">Any returned status</option>
                {["PASS", "FAIL", "MANUAL", "BLOCKED", "DATA_INSUFFICIENT", "MANUAL_REVIEW", "REJECTED", "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING", "NOT_EVALUATED"].map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </SelectInput>
              <SelectInput label="Timeframe" value={filters.timeframe} onChange={(event) => setFilters({ ...filters, timeframe: event.target.value })}>
                <option value="">Any returned timeframe</option>
                <option value="M">M</option>
                <option value="W">W</option>
                <option value="D">D</option>
              </SelectInput>
              <TextInput label="Data-quality code" value={filters.quality} onChange={(event) => setFilters({ ...filters, quality: event.target.value })} />
              <Button type="button" onClick={() => setFilters({ symbol: "", status: "", timeframe: "", quality: "" })}>
                Clear filters
              </Button>
            </div>
            <p className="text-[11px] text-muted">
              Showing {filtered.length} of {symbols.length} stored symbols. Filters do not change the envelope. Envelope candidate counts stay on the stored counts object.
            </p>
            {symbols.length === 0 ? <EmptyState title="No symbol rows" reason="The stored scan returned no symbols." /> : null}
            {symbols.length > 0 && filtered.length === 0 ? <EmptyState title="No rows match the filter" reason="The stored symbols are unchanged." /> : null}
            {filtered.length > 0 ? (
              <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
                <table className="gtf-table w-full border-collapse text-left text-[12px]">
                  <thead className="bg-surface-2">
                    <tr>
                      {["Symbol", "Symbol status", "Candidate status", "Zone", "Timeframe", "Deciding gates", "Limitations", ""].map((header) => (
                        <th key={header || "inspect"} className="border-b border-line px-2 py-2 font-medium">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((symbol, index) => (
                      <tr key={`${symbol.symbol ?? "row"}-${index}`} className="align-top">
                        <td className="border-b border-line px-2 py-2 font-medium">{symbol.symbol ?? <Unavailable />}</td>
                        <td className="border-b border-line px-2 py-2">
                          {symbolStatusOf(symbol) ? <StatusBadge code={symbolStatusOf(symbol) as string} /> : <Unavailable />}
                          {textList(symbol.reasons).length ? <p>{textList(symbol.reasons).join(" · ")}</p> : null}
                        </td>
                        <td className="border-b border-line px-2 py-2">
                          {(symbol.candidates ?? []).length === 0 ? (
                            <span>No candidate supplied</span>
                          ) : (
                            <span className="flex flex-col gap-1">
                              {(symbol.candidates ?? []).map((candidate, candidateIndex) =>
                                candidateStatusOf(candidate) ? (
                                  <StatusBadge key={`${candidateStatusOf(candidate)}-${candidateIndex}`} code={candidateStatusOf(candidate) as string} />
                                ) : (
                                  <Unavailable key={candidateIndex} />
                                ),
                              )}
                            </span>
                          )}
                        </td>
                        <td className="border-b border-line px-2 py-2">{zoneSummary(symbol)}</td>
                        <td className="border-b border-line px-2 py-2">{listedTimeframes(symbol).join(", ") || <Unavailable />}</td>
                        <td className="border-b border-line px-2 py-2">{decidingSummary(symbol)}</td>
                        <td className="border-b border-line px-2 py-2">{(symbol.limitations ?? []).join(", ") || <Unavailable />}</td>
                        <td className="border-b border-line px-2 py-2">
                          <Button type="button" disabled={!symbol.symbol} onClick={() => symbol.symbol && setSelectedSymbol(symbol.symbol)}>
                            Inspect {symbol.symbol ?? "symbol"}
                          </Button>
                          <Button
                            type="button"
                            disabled={!symbol.symbol || !requestedScan}
                            onClick={() =>
                              symbol.symbol &&
                              app.navigate("analysis", {
                                scan: requestedScan,
                                symbol: symbol.symbol,
                                as_of: envelope?.as_of,
                                dataset_id: envelope?.dataset_id,
                                ...(includeFixtures ? { fixtures: "1" } : {}),
                              })
                            }
                          >
                            Open analysis
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
      </Section>

      {selectedSymbol ? (
        <Section title={`Evidence · ${selectedSymbol}`}>
          {symbols.find((symbol) => symbol.symbol === selectedSymbol) ? (
            <SymbolEvidence symbol={symbols.find((symbol) => symbol.symbol === selectedSymbol) as ResearchSymbol} source="Scan symbol record" />
          ) : null}
          {bundleError ? <ErrorLine error={bundleError} /> : null}
          {bundleFixture || candleFixture ? <Warning>FIXTURE_NOT_MARKET_DATA</Warning> : null}
          {bundle?.stored ? <SymbolEvidence symbol={bundle.stored} source="Stored bundle" /> : null}
          {!bundle?.stored && !bundleError ? <p className="text-[12px]">Loading the stored bundle.</p> : null}
          <div className="flex flex-wrap gap-2">
            {["M", "W", "D"].map((timeframe) => (
              <Button key={timeframe} type="button" aria-pressed={candleTf === timeframe} onClick={() => setCandleTf(timeframe)}>
                {timeframe}
              </Button>
            ))}
          </div>
          {candleError ? <ErrorLine error={candleError} /> : null}
          {candles ? <CandleTable payload={candles} showAll={showAllCandles} onToggle={() => setShowAllCandles((value) => !value)} /> : null}
          <p className="text-[11px] text-muted">Candle rows are the payload returned for this as-of. Missing sessions are not filled and prices are not adjusted here.</p>
        </Section>
      ) : null}
    </section>
  );
}

function ParameterList(props: { parameters: Record<string, unknown>; ignored: string[] }) {
  const entries = Object.entries(props.parameters);
  if (entries.length === 0) return <p>No parameters stored.</p>;
  return (
    <ul>
      {entries.map(([key, value]) => (
        <li key={key}>
          {key}: {typeof value === "string" ? value : JSON.stringify(value)}
          {props.ignored.includes(key) || key.toLowerCase().includes("max_base_candles") ? " · not applied" : ""}
        </li>
      ))}
    </ul>
  );
}

function HistoryTable(props: { rows: ScanSummary[]; job: JobData | null; onOpen: (scanKey: string) => void }) {
  return (
    <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
      <table className="gtf-table w-full border-collapse text-left text-[12px]">
        <thead className="bg-surface-2">
          <tr>
            {["Scan", "Type", "As of", "Job state", "Completeness", "Dataset", "Fixture", ""].map((header) => (
              <th key={header || "open"} className="border-b border-line px-2 py-2 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row) => (
            <tr key={row.scan_key}>
              <td className="border-b border-line px-2 py-2">{row.scan_key}</td>
              <td className="border-b border-line px-2 py-2">{row.trade_type ?? <Unavailable />}</td>
              <td className="border-b border-line px-2 py-2">{row.as_of ?? <Unavailable />}</td>
              <td className="border-b border-line px-2 py-2">
                <JobState state={props.job?.result_ref === row.scan_key ? props.job.state : null} />
              </td>
              <td className="border-b border-line px-2 py-2">
                <Completeness value={row.completeness} />
              </td>
              <td className="border-b border-line px-2 py-2">{row.dataset_id ?? <Unavailable />}</td>
              <td className="border-b border-line px-2 py-2">{row.fixture ? "FIXTURE_NOT_MARKET_DATA" : "false"}</td>
              <td className="border-b border-line px-2 py-2">
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

function zoneSummary(symbol: ResearchSymbol) {
  const zones = (symbol.candidates ?? []).map((candidate) => fieldText(candidate.zone?.overlay_status)).filter((item): item is string => !!item);
  if (zones.length === 0) return <Unavailable />;
  return zones.join(", ");
}

function ScanOutcomePanel(props: { outcome: ScanOutcome | null }) {
  const outcome = props.outcome;
  if (!outcome) return null;
  return (
    <div className="space-y-1 rounded-[4px] border border-line p-2.5 text-[12px]" data-testid="scan-outcome" data-kind={outcome.kind}>
      <p className="font-medium">{outcome.headline}</p>
      {outcome.lines.map((line) => (
        <p key={`${line.code}-${line.text}`} data-code={line.code}>
          <span className="font-mono">{line.code}</span> {line.text}
        </p>
      ))}
      <p className="text-[11px] text-muted">From stored statuses and gates only. The scanner page does not re-run qualification.</p>
    </div>
  );
}

function decidingSummary(symbol: ResearchSymbol) {
  const groups = (symbol.candidates ?? []).flatMap((candidate) => candidate.deciding_gates ?? []);
  const missing = (symbol.candidates ?? []).some((candidate) => candidate.deciding_gates === undefined);
  if (groups.length === 0 && missing) return <Unavailable />;
  if (groups.length === 0) return <span>None listed</span>;
  return (
    <ul>
      {groups.map((group, index) => (
        <li key={`${group.status ?? "status"}-${index}`}>
          {group.status ?? "Status unavailable"}: {(group.gates ?? []).map((gate) => `${gate.gate ?? "gate"} ${gate.outcome ?? ""}`.trim()).join(", ") || "no gates"}
        </li>
      ))}
    </ul>
  );
}

function SymbolEvidence(props: { symbol: ResearchSymbol; source: string }) {
  const identity = props.symbol.identity ?? {};
  return (
    <div className="space-y-2 text-[12px]">
      <p className="font-semibold">{props.source}</p>
      <FactGrid>
        <Fact label="Symbol">{props.symbol.symbol ?? <Unavailable />}</Fact>
        <Fact label="Symbol status">{symbolStatusOf(props.symbol) ? <StatusBadge code={symbolStatusOf(props.symbol) as string} /> : <Unavailable />}</Fact>
        <Fact label="ISIN">{fieldText(identity.isin) ?? <Unavailable />}</Fact>
        <Fact label="ISIN status">{fieldText(identity.isin_status) ?? <Unavailable />}</Fact>
        <Fact label="Universe member">{fieldText(identity.universe_member) ?? <Unavailable />}</Fact>
      </FactGrid>
      <p>Reasons: {textList(props.symbol.reasons).join(" · ") || "None returned"}</p>
      <p>Limitations: {(props.symbol.limitations ?? []).join(", ") || "None returned"}</p>
      <p>Data-quality codes: {qualityCodes(props.symbol).join(", ") || "None returned"}</p>
      {(props.symbol.candidates ?? []).map((candidate, index) => (
        <article key={`${candidate.zone_id ?? "candidate"}-${index}`} className="rounded-[4px] border border-line p-2.5">
          <p className="font-medium">Candidate {index + 1}</p>
          <p>{candidateStatusOf(candidate) ? <StatusBadge code={candidateStatusOf(candidate) as string} /> : <Unavailable />}</p>
          <p>Zone {fieldText(candidate.zone?.zone_id) ?? "unavailable"} · overlay {fieldText(candidate.zone?.overlay_status) ?? "unavailable"} · proximal {fieldText(candidate.zone?.proximal) ?? "unavailable"} · distal {fieldText(candidate.zone?.distal) ?? "unavailable"}</p>
          <p>Score {scoreText(candidate.zone?.pre_entry_score) ?? <Unavailable />}</p>
          <ul className="mt-1 space-y-1">
            {(candidate.gates ?? []).length === 0 ? <li>Gates unavailable</li> : null}
            {(candidate.gates ?? []).map((gate) => (
              <li key={`${gate.gate}-${gate.outcome}`}>
                {gate.gate ?? "Gate"} {gate.title ? `· ${gate.title}` : ""} {gate.outcome ? <StatusBadge code={gate.outcome} /> : <Unavailable />}
                <span className="text-muted"> {textList(gate.reasons).join(" · ")}</span>
                {textList(gate.manual_review).length ? <span> Manual: {textList(gate.manual_review).join(" · ")}</span> : null}
              </li>
            ))}
          </ul>
          <p className="mt-1">Deciding gates</p>
          {candidate.deciding_gates === undefined ? <Unavailable /> : decidingSummary({ candidates: [candidate] })}
        </article>
      ))}
      <details>
        <summary>Stored symbol record</summary>
        <pre className="overflow-auto text-[11px]">{JSON.stringify(props.symbol, null, 2)}</pre>
      </details>
    </div>
  );
}

function CandleTable(props: { payload: CandlePayload; showAll: boolean; onToggle: () => void }) {
  const rows = props.payload.candles ?? [];
  const visible = props.showAll ? rows : rows.slice(-12);
  return (
    <div className="space-y-2 text-[12px]">
      <p>
        {props.payload.timeframe ?? "Timeframe unavailable"} · {rows.length} candles returned · {props.payload.available_from ?? "from unavailable"} to {props.payload.available_to ?? "to unavailable"} · volume {props.payload.volume_state ?? "unavailable"} · adjusted <Value value={props.payload.adjusted} />
      </p>
      <p>Missing sessions: {props.payload.missing_sessions?.length ?? "unavailable"}</p>
      <p>Limitations: {(props.payload.limitations ?? []).join(", ") || "None returned"}</p>
      {rows.length > 12 ? (
        <Button type="button" onClick={props.onToggle}>
          {props.showAll ? "Show the latest 12 returned bars" : `Show all ${rows.length} returned candles`}
        </Button>
      ) : null}
      <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
        <table className="gtf-table w-full border-collapse text-left text-[12px]">
          <caption className="px-2 py-1 text-left text-[11px] text-muted">Latest returned bars. Not a live price.</caption>
          <thead>
            <tr>
              {["Session", "Open", "High", "Low", "Close", "Volume"].map((header) => (
                <th key={header} className="border-b border-line px-2 py-1 font-medium">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => (
              <tr key={`${row.time ?? "t"}-${index}`}>
                <td className="border-b border-line px-2 py-1 tabular">{row.session_date ?? row.time ?? "—"}</td>
                <td className="border-b border-line px-2 py-1 tabular">{price(row.open)}</td>
                <td className="border-b border-line px-2 py-1 tabular">{price(row.high)}</td>
                <td className="border-b border-line px-2 py-1 tabular">{price(row.low)}</td>
                <td className="border-b border-line px-2 py-1 tabular">{price(row.close)}</td>
                <td className="border-b border-line px-2 py-1 tabular">{row.volume == null ? "—" : price(row.volume)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function scoreText(value: unknown): string | null {
  if (value == null || value === "") return null;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (typeof value === "object") return JSON.stringify(value);
  return null;
}

function price(value: unknown): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return "—";
}
