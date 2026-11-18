/** Display contracts copied from the platform API and the research vocabulary.
 * The UI does not derive a gate outcome or a candidate status.
 */

export const PLATFORM_SCHEMA = "gtf-platform/1";
export const FIXTURE_LABEL = "FIXTURE_NOT_MARKET_DATA";

export type Timeframe = "M" | "W" | "D";

export type GateId = "G0" | "G1" | "G2" | "G3" | "G4" | "G5" | "G6" | "G7" | "G8";

export type GateOutcome =
  | "PASS"
  | "FAIL"
  | "MANUAL"
  | "DATA_INSUFFICIENT"
  | "BLOCKED"
  | "NOT_EVALUATED";

export type CandidateStatus =
  | "BLOCKED"
  | "REJECTED"
  | "DATA_INSUFFICIENT"
  | "MANUAL_REVIEW"
  | "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING";

export type ZoneStatus = "FRESH" | "TESTED" | "INVALIDATED" | "UNKNOWN";

export interface Envelope<T> {
  platform_schema: typeof PLATFORM_SCHEMA;
  data: T;
  meta: { fixture: boolean; fixture_label?: typeof FIXTURE_LABEL };
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export type ConnectionState = "loading" | "connected" | "disconnected" | "unauthenticated" | "unavailable";

export interface HealthScan {
  scan_key: string;
  as_of: string;
  completeness: string;
  dataset_id: string;
}

export interface HealthData {
  outcome: string;
  scheduler_state: string;
  database_files: {
    platform: { configured: boolean; reachable: boolean };
    research: { configured: boolean; reachable: boolean };
  };
  last_successful_ingest_date: string | null;
  last_scan_run_id: string | null;
  last_scan: HealthScan | null;
  last_scan_state: string;
  data_limitations?: string[];
  data_ready?: boolean;
  data_ready_reason?: string;
  readiness_state?: string;
  certified_p0_data?: boolean;
  orders_placed?: boolean;
}

export interface OverviewJob {
  job_id?: string;
  state?: string;
  error_code?: string | null;
  error_message?: string | null;
  result_ref?: string | null;
}

export interface OverviewData {
  state?: string;
  as_of?: string | null;
  dataset_id?: string | null;
  counts?: OverviewCounts | null;
  calendar?: CalendarData | null;
  index?: unknown;
  sector?: unknown;
  breadth?: unknown;
  job?: OverviewJob | null;
  active_job?: OverviewJob | null;
  scan_due?: { state?: string; as_of?: string | null; reason?: string | null } | null;
  job_phase?: string;
  limitations?: string[];
  history_cut?: { applied?: boolean | null; symbols?: string[]; code?: string | null; state?: string };
  identity_findings?: string[];
  manifest_id?: string | null;
  full_universe_scan?: boolean;
  data_ready?: boolean;
  data_ready_reason?: string;
  readiness_state?: string;
  certified_p0_data?: boolean;
  coverage?: { limitations?: string[]; incomplete_symbols?: string[]; note?: string };
  authorises_order?: boolean;
}


export interface OverviewCounts {
  symbols?: number;
  candidates?: number;
  blocked_zones?: number;
  symbol_status?: Record<string, number>;
  candidate_status?: Record<string, number>;
}

export interface DatasetRow {
  dataset_id?: string;
  manifest_sha256?: string | null;
  file_count?: number;
  research_validation?: boolean;
  data_ready?: boolean;
  fixture?: boolean;
}

export interface DatasetsData {
  datasets?: DatasetRow[];
  limitations?: string[];
}

export interface UniverseMember {
  symbol?: string;
  series?: string;
  isin?: string | null;
  verified?: boolean;
}

export interface UniverseData {
  as_of?: string;
  name?: string;
  members?: UniverseMember[];
  limitations?: string[];
  certified?: boolean;
  full_universe_scan?: boolean;
}

export interface CalendarData {
  date?: string;
  status?: string;
  classification?: string | null;
  reason?: string | null;
}

export interface Instrument {
  symbol: string;
  name: string | null;
  isin: string | null;
  verified: boolean;
}

export interface WatchlistItem {
  symbol: string;
  added_at?: string | null;
  reason?: string | null;
  note?: string | null;
}

export interface Watchlist {
  watchlist_id: string;
  name: string;
  symbols: string[];
  items?: WatchlistItem[];
  eligibility?: unknown;
  authorises_order?: boolean;
  note?: string;
  created_at?: string;
  updated_at?: string;
}

export interface OrganizationalPriority {
  score: number;
  factors?: Record<string, number>;
  authoritative: boolean;
  disclosure: string;
}

export interface Opportunity {
  opportunity_id: string;
  scan_key: string;
  symbol: string;
  zone_id?: string | null;
  timeframe?: string | null;
  as_of?: string | null;
  dataset_id?: string | null;
  exchange?: string;
  canonical_status: string;
  workflow_state: string;
  source_quality: string;
  fixture?: boolean;
  authorises_order?: boolean;
  allowed_transitions?: string[];
  organizational_priority?: OrganizationalPriority;
  source_snapshot?: {
    manual_checks?: unknown;
    deciding_gates?: unknown;
    snapshot_kind?: string;
  };
  created_at?: string;
  updated_at?: string;
}

export interface OpportunityListData {
  opportunities?: Opportunity[];
  total?: number;
  counts_by_workflow?: Record<string, number>;
  priority_disclosure?: string;
  authorises_order?: boolean;
  p0_certified_discovery?: boolean;
  limitation?: string;
}

export interface ScanConfig {
  config_id: string;
  name: string;
  parameters: Record<string, unknown>;
  created_at?: string;
}

export interface JobProgress {
  done?: number;
  total?: number;
  unit?: string;
}

export interface JobError {
  code?: string;
  message?: string;
}

export interface JobData {
  job_id: string;
  kind?: string;
  state: string;
  idempotency_key?: string;
  completeness?: string | null;
  progress?: JobProgress | null;
  result_ref?: string | null;
  error?: JobError | null;
}

export interface ScanSummary {
  scan_key: string;
  as_of?: string;
  trade_type?: string;
  invocation?: string;
  dataset_id?: string;
  universe?: string;
  completeness?: string;
  full_universe_scan?: boolean;
  limitations?: string[];
  symbols_not_opened?: string[];
  fixture?: boolean;
}

export interface ScanListData {
  scans?: ScanSummary[];
  next_cursor?: string | null;
}

export interface GateRow {
  gate?: string;
  title?: string;
  outcome?: string;
  reasons?: string[];
  manual_review?: string[];
  sources?: string[];
}

export interface DecidingGateGroup {
  status?: string;
  gates?: GateRow[];
}

export interface ResearchCandidate {
  /** Canonical stored key (nse/research reports). */
  status?: string;
  /** Legacy client name; fallback only. */
  candidate_status?: string;
  status_consistent_with_gates?: boolean;
  zone_id?: string;
  created_time?: string;
  zone?: Record<string, unknown>;
  gates?: GateRow[];
  deciding_gates?: DecidingGateGroup[];
  trade_plan?: Record<string, unknown>;
}

export interface ResearchSymbol {
  symbol?: string;
  /** Canonical stored key (nse/research reports). */
  status?: string;
  /** Legacy client name; fallback only. */
  symbol_status?: string;
  reasons?: string[];
  identity?: Record<string, unknown>;
  mtf?: Record<string, unknown>;
  findings?: unknown[];
  limitations?: string[];
  blocked_zones?: unknown[];
  candidates?: ResearchCandidate[];
}

export interface ResearchEnvelope {
  schema?: string;
  as_of?: string;
  trade_type?: string;
  invocation?: string;
  dataset_id?: string | null;
  completeness?: string;
  symbols_not_opened?: string[];
  full_universe_scan?: boolean;
  methodology?: Record<string, unknown>;
  ranking?: string;
  authorises_order?: boolean;
  order_note?: string;
  research_notes?: string[];
  limitations?: string[];
  counts?: OverviewCounts;
  symbols?: ResearchSymbol[];
  trade_plans?: Record<string, unknown>[];
}

export interface ScanSymbolsData {
  scan_key?: string;
  symbols?: ResearchSymbol[];
  symbols_not_opened?: string[];
}

export interface SymbolBundle {
  scan_key?: string;
  dataset_id?: string | null;
  as_of?: string;
  trade_type?: string;
  completeness?: string;
  full_universe_scan?: boolean;
  symbols_not_opened?: string[];
  limitations?: string[];
  authorises_order?: boolean;
  replay?: unknown;
  stored?: ResearchSymbol;
}

export interface CandleRow {
  time?: string;
  session_date?: string;
  open?: string | number;
  high?: string | number;
  low?: string | number;
  close?: string | number;
  volume?: string | number | null;
  /** W/M only: constituent daily sessions summed into volume. */
  volume_sessions?: number | null;
}

export interface CandleDataQuality {
  research_use?: string;
  certified?: boolean;
  certification_note?: string;
  fixture?: boolean;
  identity_status?: string;
  price_adjustment?: string;
  volume_state?: string;
  volume_source?: string | null;
  adjusted?: boolean;
  data_ready?: boolean;
}

export interface CandlePayload {
  symbol?: string;
  timeframe?: string;
  dataset_id?: string;
  requested_as_of?: string;
  available_from?: string | null;
  available_to?: string | null;
  limitations?: string[];
  missing_sessions?: string[];
  excluded_sessions?: Array<{ date?: string; classification?: string }>;
  invalid_candles?: Array<{ session_date?: string; codes?: string[] }>;
  candles?: CandleRow[];
  volume_state?: string;
  volume_unit?: string | null;
  volume_source?: string | null;
  adjusted?: boolean;
  data_quality?: CandleDataQuality;
}

export interface GateView {
  gate: GateId;
  title: string;
  outcome: string;
  reasons: string[];
}

export interface ZoneView {
  source: "engine";
  engineId: string;
  symbol: string;
  timeframe: Timeframe;
  side: "demand" | "supply";
  startTime: string;
  createdTime: string;
  proximal: number;
  distal: number;
  overlayStatus: ZoneStatus;
  label: string;
  pattern?: string;
  engineStatus?: string;
  disposition?: string;
  testCount?: number;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  /** Traded quantity when known; null when unavailable. Never invent zero. */
  volume: number | null;
}
