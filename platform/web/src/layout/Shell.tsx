import { useEffect, useState } from "react";
import { ROUTE_GROUPS, ROUTES, routeDef, type RouteId } from "../navigation/routes";
import { apiStatusLabel, sessionLabel } from "../services/connection";
import { useAppState } from "../state/store";
import { Screen } from "../features/pages";
import { InstrumentSearch } from "./InstrumentSearch";
import { Icon } from "./icons";

export function Shell() {
  const app = useAppState();
  const [compact, setCompact] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT");
      if (event.key === "/" && !typing) {
        event.preventDefault();
        document.getElementById("global-search")?.focus();
      }
      if (event.key === "Escape") {
        (document.activeElement as HTMLElement | null)?.blur();
        setNavOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(max-width: 1100px)");
    const apply = () => setCompact(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const current = routeDef(app.route);
  const narrow = (compact || app.collapsed) && !navOpen;
  const connected = app.connection === "connected";
  const alert =
    app.connection === "disconnected"
      ? `API disconnected. ${app.error?.message ?? "Local API is not reachable"} (${app.error?.code ?? "DISCONNECTED"})`
      : app.connection === "unauthenticated"
        ? `Authentication required. ${app.error?.message ?? "Session is missing or expired"} (${app.error?.code ?? "UNAUTHENTICATED"})`
        : app.connection === "unavailable"
          ? `API unavailable. ${app.error?.message ?? "The API did not return a usable status"} (${app.error?.code ?? "UNAVAILABLE"})`
          : null;
  const dot =
    app.connection === "connected"
      ? "bg-[var(--gtf-ok)]"
      : app.connection === "loading"
        ? "bg-[var(--gtf-muted)]"
        : "bg-[var(--gtf-fail)]";
  const health = connected ? app.health : null;
  const scan = health?.last_scan ?? null;

  return (
    <div className="flex min-h-full flex-col bg-canvas text-ink">
      {app.showFixture ? (
        <div className="fixture-banner px-3 py-1 text-center text-[11.5px]" role="status">
          FIXTURE_NOT_MARKET_DATA
        </div>
      ) : null}
      <div className="relative flex flex-1">
        {compact && navOpen ? (
          <button type="button" aria-label="Close navigation overlay" className="fixed inset-0 z-20 bg-black/40" onClick={() => setNavOpen(false)} />
        ) : null}
        <nav
          aria-label="Primary"
          data-compact={compact ? "true" : "false"}
          className={`z-30 shrink-0 border-r border-line bg-[var(--gtf-nav)] ${narrow ? "w-[56px]" : "w-[232px]"} ${
            compact && navOpen ? "fixed inset-y-0 left-0 shadow-[var(--gtf-shadow-lg)]" : ""
          }`}
        >
          <div className="scroll-thin sticky top-0 flex h-screen flex-col overflow-y-auto">
          <div className={`flex h-12 shrink-0 items-center gap-2 border-b border-line ${narrow ? "justify-center px-0" : "px-3.5"}`}>
            <span aria-hidden="true" className="flex h-7 w-7 items-center justify-center rounded-[5px] bg-[var(--gtf-accent)] text-[12px] font-bold tracking-tight text-[var(--gtf-accent-ink)]">
              G
            </span>
            <div className={narrow ? "sr-only" : "min-w-0 leading-tight"}>
              <p className="text-[13px] font-semibold tracking-[0.02em]">GTF</p>
              <p className="text-[10.5px] text-muted">Trading Intelligence</p>
            </div>
          </div>
          {compact ? (
            <button
              type="button"
              className={`flex h-9 items-center gap-2 border-b border-line text-[11.5px] text-muted hover:text-ink ${narrow ? "justify-center" : "px-3.5"}`}
              onClick={() => setNavOpen((value) => !value)}
            >
              <Icon name={navOpen ? "collapse" : "expand"} size={14} />
              <span className={narrow ? "sr-only" : ""}>{navOpen ? "Close navigation" : "Open navigation"}</span>
            </button>
          ) : null}
          <div className="flex-1 py-2">
            {ROUTE_GROUPS.map((group) => (
              <div key={group} className="pb-2">
                <p className={narrow ? "sr-only" : "eyebrow px-3.5 pb-1 pt-2"}>{group}</p>
                {narrow ? <div aria-hidden="true" className="mx-3 my-1.5 border-t border-line" /> : null}
                {ROUTES.filter((route) => route.group === group).map((route) => {
                  const active = app.route === route.id;
                  return (
                    <div key={route.id} className="relative flex items-center">
                      <a
                        href={`#/${route.id}`}
                        aria-current={active ? "page" : undefined}
                        title={route.available ? route.label : `${route.label}. Not available yet`}
                        onClick={(event) => {
                          event.preventDefault();
                          app.setRoute(route.id);
                          setNavOpen(false);
                        }}
                        className={`mx-1.5 flex h-8 min-w-0 flex-1 items-center gap-2.5 rounded-[4px] text-[12.5px] ${narrow ? "justify-center" : "px-2"} ${
                          active
                            ? "bg-[var(--gtf-accent-bg)] font-semibold text-[var(--gtf-accent)]"
                            : route.available
                              ? "text-ink-2 hover:bg-surface-2 hover:text-ink"
                              : "text-muted hover:bg-surface-2"
                        }`}
                      >
                        <Icon name={route.id} />
                        <span className={narrow ? "sr-only" : "truncate"}>{route.label}</span>
                      </a>
                      {!narrow && route.status !== "LIVE" ? (
                        <span
                          className="pointer-events-none absolute right-3 rounded-[3px] border border-dashed border-line-strong px-1 text-[9.5px] font-semibold uppercase tracking-wide text-muted"
                          title={route.status === "NOT_IMPLEMENTED" ? "No backend yet" : "Some capability has no backend"}
                        >
                          {route.available ? "Partial" : "Later"}
                        </span>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
          <div className="border-t border-line">
            {!compact ? (
              <button
                type="button"
                className={`flex h-9 w-full items-center gap-2 text-[11.5px] text-muted hover:text-ink ${narrow ? "justify-center" : "px-3.5"}`}
                onClick={() => app.setCollapsed(!app.collapsed)}
                aria-pressed={app.collapsed}
              >
                <Icon name={app.collapsed ? "expand" : "collapse"} size={14} />
                <span className={narrow ? "sr-only" : ""}>{app.collapsed ? "Expand navigation" : "Collapse"}</span>
              </button>
            ) : null}
            <div className={`flex items-start gap-2 border-t border-line py-2.5 text-[10.5px] leading-snug text-muted ${narrow ? "justify-center" : "px-3.5"}`}>
              <Icon name="shield" size={13} className="mt-[1px] shrink-0" />
              <span className={narrow ? "sr-only" : ""}>No broker connection. No orders are placed. Execute manually in Kite.</span>
            </div>
          </div>
          </div>
        </nav>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex min-h-12 shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-surface px-5 py-1.5">
            <div className="min-w-0">
              <p className="text-[10.5px] text-muted">
                GTF Trading Intelligence <span aria-hidden="true">›</span> {current.group}
              </p>
              <p className="truncate text-[13px] font-semibold">{current.label}</p>
            </div>
            <div className="hidden min-w-0 flex-1 flex-wrap items-center gap-1.5 text-[11px] lg:flex" aria-label="Data context">
              <ContextChip label="EOD through" value={connected ? health?.last_successful_ingest_date ?? null : null} />
              <ContextChip label="Last scan" value={connected ? scan?.as_of?.slice(0, 10) ?? null : null} />
              <ContextChip
                label="Completeness"
                value={connected ? scan?.completeness ?? health?.last_scan_state ?? null : null}
                tone={scan?.completeness === "COMPLETE" ? undefined : "manual"}
              />
              <ContextChip
                label="P0 data"
                value={connected ? (health?.certified_p0_data === true ? "certified" : "not certified") : null}
                tone={health?.certified_p0_data === true ? undefined : "manual"}
              />
            </div>
            <p className="sr-only">
              Research and decision support. This application does not place orders. A plan is not a trade. You decide, then act in Kite.
            </p>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <InstrumentSearch />
              <p className="flex items-center gap-1.5 whitespace-nowrap text-[11.5px] text-ink-2" role="status" title={`Session ${sessionLabel(app.connection)}`}>
                <span aria-hidden="true" className={`inline-block h-2 w-2 rounded-full ${dot}`} />
                {apiStatusLabel(app.connection)}
                <span className="sr-only">. Session {sessionLabel(app.connection)}.</span>
              </p>
              <ThemeSwitch />
              <time className="tabular hidden whitespace-nowrap text-[11px] text-muted sm:inline" dateTime={now.toISOString()} title="Wall clock. Data is end of day, not live.">
                {new Intl.DateTimeFormat("en-IN", {
                  timeZone: "Asia/Kolkata",
                  hour: "2-digit",
                  minute: "2-digit",
                  day: "2-digit",
                  month: "short",
                  hourCycle: "h23",
                }).format(now)}{" "}
                IST
              </time>
            </div>
          </header>
          {alert ? (
            <div
              className="flex flex-wrap items-center gap-3 border-b border-[var(--gtf-fail)]/40 bg-[var(--gtf-fail-bg)] px-5 py-2 text-[12px] text-[var(--gtf-fail)]"
              role="alert"
            >
              <span className="font-medium">{alert}</span>
              <button type="button" className="rounded-[4px] border border-line-strong bg-surface px-2 py-0.5 text-ink" onClick={app.reload}>
                Retry
              </button>
              <FixtureToggle />
            </div>
          ) : (
            <div className="flex items-center justify-between gap-3 border-b border-line bg-surface-2 px-5 py-1 text-[11px] text-muted">
              <span>Research and decision support · End-of-day NSE data · Nothing on this screen is an order or a live quote.</span>
              <FixtureToggle />
            </div>
          )}
          <main className="flex min-w-0 flex-1 flex-col">
            <Screen route={app.route} />
          </main>
        </div>
      </div>
      {app.toast ? (
        <div role="status" className="fixed bottom-4 right-4 z-50 max-w-sm rounded-[5px] border border-line bg-elevated px-3 py-2 text-[12px] shadow-[var(--gtf-shadow-lg)]">
          {app.toast}
        </div>
      ) : null}
    </div>
  );
}

function FixtureToggle() {
  const app = useAppState();
  return (
    <button
      type="button"
      className="rounded-[4px] border border-line-strong bg-surface px-2 py-0.5 text-[11px] text-ink-2 hover:text-ink"
      onClick={() => app.setFixture(!app.fixture)}
    >
      {app.fixture ? "Hide fixture specimens" : "Show fixture specimens"}
    </button>
  );
}

export function ThemeSwitch() {
  const app = useAppState();
  const next = app.theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => app.setTheme(next)}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
      className="flex h-8 items-center gap-1.5 rounded-[4px] border border-line-strong bg-surface px-2 text-[11.5px] text-ink-2 hover:text-ink"
    >
      <Icon name={app.theme === "dark" ? "moon" : "sun"} size={14} />
      <span className="hidden xl:inline">{app.theme === "dark" ? "Dark" : "Light"}</span>
    </button>
  );
}

function ContextChip(props: { label: string; value: string | null; tone?: "manual" }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-[3px] border border-line bg-surface-2 px-1.5 py-[2px]">
      <span className="text-muted">{props.label}</span>
      <span className={`tabular font-medium ${props.value === null ? "text-muted" : props.tone === "manual" ? "text-[var(--gtf-manual)]" : "text-ink"}`}>
        {props.value ?? "unavailable"}
      </span>
    </span>
  );
}

export type { RouteId };
