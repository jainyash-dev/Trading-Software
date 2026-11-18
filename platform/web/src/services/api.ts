import {
  PLATFORM_SCHEMA,
  type ApiErrorBody,
  type ConnectionState,
  type Envelope,
  type HealthData,
} from "../types/contracts";

export interface ApiFailure {
  ok: false;
  status: number;
  error: ApiErrorBody;
}

export interface ApiSuccess<T> {
  ok: true;
  status: number;
  envelope: Envelope<T>;
}

export type ApiResult<T> = ApiSuccess<T> | ApiFailure;

const REQUEST_HEADER = "X-GTF-Request";

export function requestHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  headers.set(REQUEST_HEADER, "1");
  return headers;
}

export function parseError(body: unknown, status: number): ApiErrorBody {
  if (isRecord(body) && isRecord(body.error) && typeof body.error.code === "string") {
    return {
      code: body.error.code,
      message: typeof body.error.message === "string" ? body.error.message : "Request failed",
      details: isRecord(body.error.details) ? body.error.details : {},
    };
  }
  return {
    code: status === 0 ? "DISCONNECTED" : "REQUEST_INVALID",
    message: status === 0 ? "Local API is not reachable" : "The response was not a platform envelope",
    details: {},
  };
}

export function parseEnvelope<T>(body: unknown): Envelope<T> {
  if (!isRecord(body) || body.platform_schema !== PLATFORM_SCHEMA || !isRecord(body.meta)) {
    throw new Error("envelope");
  }
  if (typeof body.meta.fixture !== "boolean") throw new Error("envelope");
  if (body.meta.fixture === true && body.meta.fixture_label !== "FIXTURE_NOT_MARKET_DATA") {
    throw new Error("envelope");
  }
  return body as unknown as Envelope<T>;
}

export interface RequestInitOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  idempotencyKey?: string;
  query?: Record<string, string | number | boolean | null | undefined>;
}

export function withQuery(path: string, query?: RequestInitOptions["query"]): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    params.set(key, String(value));
  }
  const text = params.toString();
  if (!text) return path;
  return `${path}?${text}`;
}

export async function apiRequest<T>(
  fetchImpl: typeof fetch,
  path: string,
  init: RequestInitOptions = {},
): Promise<ApiResult<T>> {
  let response: Response;
  const headers = requestHeaders(init.body === undefined ? undefined : { "Content-Type": "application/json" });
  if (init.idempotencyKey) headers.set("Idempotency-Key", init.idempotencyKey);
  try {
    response = await fetchImpl(withQuery(path, init.query), {
      method: init.method ?? "GET",
      credentials: "include",
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      signal: init.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    return { ok: false, status: 0, error: parseError(null, 0) };
  }
  const text = await response.text();
  let json: unknown = null;
  if (text) {
    try {
      json = JSON.parse(text) as unknown;
    } catch {
      return { ok: false, status: response.status, error: parseError(null, response.status) };
    }
  }
  if (!response.ok) return { ok: false, status: response.status, error: parseError(json, response.status) };
  try {
    return { ok: true, status: response.status, envelope: parseEnvelope<T>(json) };
  } catch {
    return { ok: false, status: response.status, error: parseError(null, response.status) };
  }
}

export interface Probe {
  connection: Exclude<ConnectionState, "loading">;
  health: HealthData | null;
  fixtureFromApi: boolean;
  error: ApiErrorBody | null;
}

/** One bootstrap retry after HTTP 401. The bootstrap call itself is not retried. */
export async function apiCall<T>(
  fetchImpl: typeof fetch,
  path: string,
  init: RequestInitOptions = {},
  retryAuth = true,
): Promise<ApiResult<T>> {
  const first = await apiRequest<T>(fetchImpl, path, init);
  if (first.ok || first.status !== 401 || !retryAuth) return first;
  const boot = await apiRequest(fetchImpl, "/api/v1/session/bootstrap", { method: "POST", signal: init.signal });
  if (!boot.ok) return { ok: false, status: boot.status, error: boot.error };
  return apiRequest<T>(fetchImpl, path, init);
}

function failureProbe(result: ApiFailure): Probe {
  if (result.status === 0) {
    return { connection: "disconnected", health: null, fixtureFromApi: false, error: result.error };
  }
  if (result.status === 401 || result.error.code === "UNAUTHENTICATED") {
    return { connection: "unauthenticated", health: null, fixtureFromApi: false, error: result.error };
  }
  return { connection: "unavailable", health: null, fixtureFromApi: false, error: result.error };
}

/** Opens a session and reads health. A failure stays a failure. Fixtures are not substituted. */
export async function probeApi(fetchImpl: typeof fetch, signal?: AbortSignal): Promise<Probe> {
  const session = await apiCall(fetchImpl, "/api/v1/session", { signal });
  if (!session.ok) return failureProbe(session);
  const health = await apiCall<HealthData>(fetchImpl, "/api/v1/health", { signal });
  if (!health.ok) return failureProbe(health);
  return {
    connection: "connected",
    health: health.envelope.data,
    fixtureFromApi: health.envelope.meta.fixture,
    error: null,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
