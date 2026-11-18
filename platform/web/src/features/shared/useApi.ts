import { useEffect, useId, useState } from "react";
import { useAppState } from "../../state/store";
import type { ApiErrorBody } from "../../types/contracts";

export type Slot<T> =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "ready"; data: T; fixture: boolean }
  | { state: "error"; error: ApiErrorBody; status: number };

/**
 * Read-only GET helper for P10 screens. It never substitutes data: a failure stays a failure.
 * `path` null means "do not request" (e.g. a required input is missing).
 */
export function useApi<T>(path: string | null, query?: Record<string, string | number | boolean | undefined>, reloadKey = 0): Slot<T> {
  const app = useAppState();
  const [slot, setSlot] = useState<Slot<T>>({ state: "idle" });
  const live = app.connection === "connected";
  const queryKey = JSON.stringify(query ?? {});
  useEffect(() => {
    if (!live || !path) {
      setSlot({ state: "idle" });
      return;
    }
    const controller = new AbortController();
    let active = true;
    setSlot({ state: "loading" });
    const parsed = JSON.parse(queryKey) as Record<string, string | number | boolean>;
    app
      .request<T>(path, { query: parsed, signal: controller.signal })
      .then((result) => {
        if (!active) return;
        if (result.ok) setSlot({ state: "ready", data: result.envelope.data, fixture: result.envelope.meta.fixture });
        else {
          if (result.status === 0 || result.status === 401) app.reportFailure(result);
          setSlot({ state: "error", error: result.error, status: result.status });
        }
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (active) setSlot({ state: "error", error: { code: "DISCONNECTED", message: "Local API is not reachable", details: {} }, status: 0 });
      });
    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, path, queryKey, reloadKey, app.revision]);
  // P10 review: fixture payloads read by P10 screens also raise the global FIXTURE_NOT_MARKET_DATA banner.
  const fixture = slot.state === "ready" && slot.fixture;
  const noteFixture = app.noteFixture;
  const scope = `api:${useId()}`;
  useEffect(() => {
    noteFixture(scope, fixture);
    return () => noteFixture(scope, false);
  }, [noteFixture, scope, fixture]);
  return slot;
}

export function dataOf<T>(slot: Slot<T>): T | null {
  return slot.state === "ready" ? slot.data : null;
}
