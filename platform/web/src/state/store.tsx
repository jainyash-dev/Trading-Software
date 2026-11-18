import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { parseHash, type RouteId } from "../navigation/routes";
import { apiCall, type ApiFailure, probeApi } from "../services/api";
import type { ApiErrorBody, ConnectionState, HealthData } from "../types/contracts";

interface AppState {
  theme: "dark" | "light";
  setTheme: (theme: "dark" | "light") => void;
  collapsed: boolean;
  setCollapsed: (value: boolean) => void;
  fixture: boolean;
  setFixture: (value: boolean) => void;
  showFixture: boolean;
  noteFixture: (scope: string, value: boolean) => void;
  connection: ConnectionState;
  health: HealthData | null;
  error: ApiErrorBody | null;
  fixtureFromApi: boolean;
  route: RouteId;
  queryString: string;
  setRoute: (route: RouteId) => void;
  navigate: (route: RouteId, params?: Record<string, string | null | undefined>) => void;
  toast: string | null;
  notify: (message: string) => void;
  reload: () => void;
  revision: number;
  reportFailure: (result: ApiFailure) => void;
  request: <T>(path: string, init?: Parameters<typeof apiCall>[2]) => ReturnType<typeof apiCall<T>>;
}

const Context = createContext<AppState | null>(null);

export function AppStateProvider(props: { children: ReactNode; fetcher?: typeof fetch }) {
  const fallbackFetch = useRef(window.fetch.bind(window));
  const fetcher = props.fetcher ?? fallbackFetch.current;
  const [theme, setThemeState] = useState<"dark" | "light">(() => (readPreference("gtf-theme") === "light" ? "light" : "dark"));
  const [collapsed, setCollapsedState] = useState(() => readPreference("gtf-sidebar") === "collapsed");
  const [fixture, setFixture] = useState(() => new URLSearchParams(window.location.search).get("fixtures") === "1");
  const [fixtureScopes, setFixtureScopes] = useState<Record<string, boolean>>({});
  const [connection, setConnection] = useState<ConnectionState>("loading");
  const [health, setHealth] = useState<HealthData | null>(null);
  const [error, setError] = useState<ApiErrorBody | null>(null);
  const [fixtureFromApi, setFixtureFromApi] = useState(false);
  const initial = parseHash(window.location.hash);
  const [route, setRouteState] = useState<RouteId>(initial.route);
  const [queryString, setQueryString] = useState(initial.query);
  const [toast, setToast] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    writePreference("gtf-theme", theme);
  }, [theme]);

  useEffect(() => {
    writePreference("gtf-sidebar", collapsed ? "collapsed" : "open");
  }, [collapsed]);

  useEffect(() => {
    const controller = new AbortController();
    setConnection("loading");
    void probeApi(fetcher, controller.signal).then((probe) => {
      if (controller.signal.aborted) return;
      setConnection(probe.connection);
      setHealth(probe.health);
      setError(probe.error);
      setFixtureFromApi(probe.fixtureFromApi);
    });
    return () => controller.abort();
  }, [attempt, fetcher]);

  useEffect(() => {
    const onHash = () => {
      const next = parseHash(window.location.hash);
      setRouteState(next.route);
      setQueryString(next.query);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const noteFixture = useCallback((scope: string, value: boolean) => {
    setFixtureScopes((current) => (current[scope] === value ? current : { ...current, [scope]: value }));
  }, []);

  const reportFailure = useCallback((result: ApiFailure) => {
    setError(result.error);
    if (result.status === 0) setConnection("disconnected");
    else if (result.status === 401 || result.error.code === "UNAUTHENTICATED") setConnection("unauthenticated");
    else if (result.status >= 500) setConnection("unavailable");
  }, []);

  const request = useCallback(
    <T,>(path: string, init?: Parameters<typeof apiCall>[2]) => apiCall<T>(fetcher, path, init),
    [fetcher],
  );

  const setRoute = useCallback((next: RouteId) => {
    window.location.hash = `/${next}`;
    setRouteState(next);
    setQueryString("");
  }, []);

  const navigate = useCallback((next: RouteId, params?: Record<string, string | null | undefined>) => {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params ?? {})) {
      if (value) search.set(key, value);
    }
    const qs = search.toString();
    window.location.hash = qs ? `/${next}?${qs}` : `/${next}`;
    setRouteState(next);
    setQueryString(qs);
  }, []);

  const showFixture = fixture || fixtureFromApi || Object.values(fixtureScopes).some(Boolean);

  const value = useMemo<AppState>(
    () => ({
      theme,
      setTheme: setThemeState,
      collapsed,
      setCollapsed: setCollapsedState,
      fixture,
      setFixture: (next) => {
        setFixture(next);
        if (next) setToast("Fixture specimens are on screen. They are not market data.");
      },
      showFixture,
      noteFixture,
      connection,
      health,
      error,
      fixtureFromApi,
      route,
      queryString,
      setRoute,
      navigate,
      toast,
      notify: setToast,
      reload: () => setAttempt((current) => current + 1),
      revision: attempt,
      reportFailure,
      request,
    }),
    [
      theme,
      collapsed,
      fixture,
      showFixture,
      noteFixture,
      connection,
      health,
      error,
      fixtureFromApi,
      route,
      queryString,
      setRoute,
      navigate,
      toast,
      reportFailure,
      request,
      attempt,
    ],
  );

  return <Context.Provider value={value}>{props.children}</Context.Provider>;
}

/** Display preferences only. Storage can be unavailable (private mode); the app still works. */
function readPreference(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writePreference(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* preference not persisted */
  }
}

export function useAppState(): AppState {
  const value = useContext(Context);
  if (!value) throw new Error("AppStateProvider is missing");
  return value;
}
