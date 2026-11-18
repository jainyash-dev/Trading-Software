import { useEffect, useRef, useState, type ReactNode } from "react";
import { presentLimitation, presentStatus, statusRank, unavailableText } from "./status";

/* ------------------------------------------------------------------ Page */

export function Page(props: {
  title: string;
  description: string;
  actions?: ReactNode;
  eyebrow?: string;
  meta?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="flex min-w-0 flex-1 flex-col gap-4 px-5 py-4">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3">
        <div className="min-w-0">
          {props.eyebrow ? <p className="eyebrow">{props.eyebrow}</p> : null}
          <h1 className="mt-0.5 text-[19px] font-semibold leading-6 tracking-[-0.01em]">{props.title}</h1>
          <p className="mt-1 max-w-4xl text-[12.5px] leading-[1.5] text-muted">{props.description}</p>
          {props.meta ? <div className="mt-2 flex flex-wrap items-center gap-2">{props.meta}</div> : null}
        </div>
        {props.actions ? <div className="flex flex-wrap items-center gap-2">{props.actions}</div> : null}
      </header>
      {props.children}
    </section>
  );
}

/* --------------------------------------------------------------- Panels */

export function Panel(props: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  id?: string;
  flush?: boolean;
  className?: string;
  testId?: string;
}) {
  return (
    <section id={props.id} className={`panel min-w-0 ${props.className ?? ""}`} data-testid={props.testId}>
      {props.title || props.actions ? (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3.5 py-2.5">
          <div className="min-w-0">
            {props.title ? <h2 className="text-[13px] font-semibold leading-5">{props.title}</h2> : null}
            {props.subtitle ? <p className="text-[11.5px] text-muted">{props.subtitle}</p> : null}
          </div>
          {props.actions ? <div className="flex flex-wrap items-center gap-2">{props.actions}</div> : null}
        </header>
      ) : null}
      <div className={props.flush ? "" : "space-y-3 p-3.5"}>{props.children}</div>
    </section>
  );
}

export type Tone = "neutral" | "ok" | "fail" | "manual" | "info";

const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-ink",
  ok: "text-[var(--gtf-ok)]",
  fail: "text-[var(--gtf-fail)]",
  manual: "text-[var(--gtf-manual)]",
  info: "text-[var(--gtf-info)]",
};

/** A financial or operational figure. `value` null renders the Unavailable state, never zero. */
export function Metric(props: {
  label: string;
  value: ReactNode | null;
  unit?: string;
  sub?: ReactNode;
  tone?: Tone;
  testId?: string;
  children?: ReactNode;
}) {
  return (
    <div className="panel min-w-0 px-3.5 py-3">
      <p className="eyebrow">{props.label}</p>
      <div className={`mt-1 flex items-baseline gap-1 text-[20px] font-semibold leading-7 tabular ${TONE_TEXT[props.tone ?? "neutral"]}`} data-testid={props.testId}>
        {props.value === null ? <span className="text-[14px] font-normal text-muted">— {unavailableText()}</span> : props.value}
        {props.value !== null && props.unit ? <span className="text-[12px] font-normal text-muted">{props.unit}</span> : null}
      </div>
      {props.sub ? <div className="mt-1 text-[11.5px] leading-4 text-muted">{props.sub}</div> : null}
      {props.children}
    </div>
  );
}

/** Usage against a cap (e.g. "7 of 10"). The text carries the meaning; the bar is decoration. */
export function Meter(props: { value: number | null; max: number | null; label: string }) {
  const ratio = props.value !== null && props.max ? Math.min(1, Math.max(0, props.value / props.max)) : 0;
  const tone = ratio >= 1 ? "var(--gtf-fail)" : ratio >= 0.8 ? "var(--gtf-manual)" : "var(--gtf-accent)";
  return (
    <div className="mt-2" aria-hidden="true" title={props.label}>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--gtf-neutral-bg)]">
        <div className="h-full rounded-full" style={{ width: `${ratio * 100}%`, background: tone }} />
      </div>
    </div>
  );
}

export function KeyValue(props: { rows: Array<[string, ReactNode]>; columns?: 1 | 2 }) {
  return (
    <dl className={`grid gap-x-6 gap-y-0 text-[12.5px] ${props.columns === 2 ? "sm:grid-cols-2" : ""}`}>
      {props.rows.map(([label, value]) => (
        <div key={label} className="flex min-w-0 items-baseline justify-between gap-3 border-b border-line py-1.5 last:border-b-0">
          <dt className="shrink-0 text-muted">{label}</dt>
          <dd className="min-w-0 break-words text-right">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/* --------------------------------------------------------------- Status */

export function StatusBadge({ code }: { code: string }) {
  const status = presentStatus(code);
  const tone = {
    ok: "bg-[var(--gtf-ok-bg)] text-[var(--gtf-ok)]",
    fail: "bg-[var(--gtf-fail-bg)] text-[var(--gtf-fail)]",
    manual: "bg-[var(--gtf-manual-bg)] text-[var(--gtf-manual)]",
    neutral: "bg-[var(--gtf-neutral-bg)] text-[var(--gtf-neutral-ink)]",
    blocked: "bg-[var(--gtf-blocked-bg)] text-[var(--gtf-blocked-ink)]",
    unknown: "bg-[var(--gtf-neutral-bg)] text-[var(--gtf-muted)]",
  }[status.tone];
  const border = status.dashed ? "border-dashed border-current/60" : "border-transparent";
  return (
    <span
      className={`inline-flex max-w-full items-center gap-1 rounded-[3px] border px-1.5 py-[1px] text-[11px] font-medium leading-4 ${tone} ${border}`}
      data-status={status.code}
    >
      <span aria-hidden="true">{status.tone === "unknown" ? "?" : status.tone === "fail" ? "×" : status.tone === "ok" ? "✓" : "•"}</span>
      {status.label}
    </span>
  );
}

/** Data provenance labels (P10 section 15). Only render a label the backend state supports. */
export type Provenance = "CERTIFIED" | "PROVISIONAL" | "FIXTURE" | "STALE" | "UNAVAILABLE" | "NOT_IMPLEMENTED" | "BLOCKED" | "EXPLORATORY" | "PARTIAL" | "LIVE";

const PROVENANCE: Record<Provenance, { label: string; className: string; glyph: string }> = {
  CERTIFIED: { label: "CERTIFIED", className: "bg-[var(--gtf-ok-bg)] text-[var(--gtf-ok)]", glyph: "✓" },
  PROVISIONAL: { label: "PROVISIONAL", className: "bg-[var(--gtf-manual-bg)] text-[var(--gtf-manual)] border-dashed", glyph: "◐" },
  EXPLORATORY: { label: "EXPLORATORY · NOT CERTIFIED", className: "bg-[var(--gtf-manual-bg)] text-[var(--gtf-manual)] border-dashed", glyph: "◐" },
  FIXTURE: { label: "FIXTURE", className: "bg-[var(--gtf-manual-bg)] text-[var(--gtf-manual)]", glyph: "◇" },
  STALE: { label: "STALE", className: "bg-[var(--gtf-manual-bg)] text-[var(--gtf-manual)] border-dashed", glyph: "◷" },
  UNAVAILABLE: { label: "UNAVAILABLE", className: "bg-[var(--gtf-neutral-bg)] text-[var(--gtf-muted)] border-dashed", glyph: "—" },
  NOT_IMPLEMENTED: { label: "NOT_IMPLEMENTED", className: "bg-[var(--gtf-neutral-bg)] text-[var(--gtf-muted)] border-dashed", glyph: "○" },
  BLOCKED: { label: "BLOCKED", className: "bg-[var(--gtf-blocked-bg)] text-[var(--gtf-blocked-ink)]", glyph: "■" },
  PARTIAL: { label: "PARTIAL", className: "bg-[var(--gtf-info-bg)] text-[var(--gtf-info)] border-dashed", glyph: "◑" },
  LIVE: { label: "CONNECTED", className: "bg-[var(--gtf-info-bg)] text-[var(--gtf-info)]", glyph: "●" },
};

export function ProvenanceBadge(props: { kind: Provenance; title?: string }) {
  const item = PROVENANCE[props.kind];
  return (
    <span
      title={props.title}
      data-provenance={props.kind}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-[3px] border border-current/40 px-1.5 py-[1px] text-[10.5px] font-semibold tracking-[0.03em] ${item.className}`}
    >
      <span aria-hidden="true">{item.glyph}</span>
      {item.label}
    </span>
  );
}

export function Limitation({ code }: { code: string }) {
  return <span className="text-[12px] text-muted">{presentLimitation(code)}</span>;
}

export function Unavailable() {
  return (
    <span className="text-muted">
      <span className="tabular">—</span> {unavailableText()}
    </span>
  );
}

export function Numeric({ value }: { value: number | null }) {
  if (value === null) return <Unavailable />;
  return <span className="tabular">{value}</span>;
}

export function PriceChange({ value }: { value: number | null }) {
  if (value === null) return <Unavailable />;
  const direction = value > 0 ? "up" : value < 0 ? "down" : "flat";
  const color = direction === "up" ? "text-[var(--gtf-ok)]" : direction === "down" ? "text-[var(--gtf-fail)]" : "text-muted";
  return (
    <span className={`tabular ${color}`}>
      {value > 0 ? "+" : ""}
      {value.toFixed(2)} {direction}
    </span>
  );
}

/* -------------------------------------------------------------- Notices */

const CALLOUT: Record<Tone, string> = {
  neutral: "border-line bg-surface-2 text-ink-2",
  info: "border-[var(--gtf-info)]/40 bg-[var(--gtf-info-bg)] text-[var(--gtf-info)]",
  manual: "border-[var(--gtf-manual)]/50 bg-[var(--gtf-manual-bg)] text-[var(--gtf-manual)]",
  fail: "border-[var(--gtf-fail)]/50 bg-[var(--gtf-fail-bg)] text-[var(--gtf-fail)]",
  ok: "border-[var(--gtf-ok)]/40 bg-[var(--gtf-ok-bg)] text-[var(--gtf-ok)]",
};

const CALLOUT_GLYPH: Record<Tone, string> = { neutral: "i", info: "i", manual: "!", fail: "×", ok: "✓" };

export function Callout(props: { tone?: Tone; title?: ReactNode; children?: ReactNode; role?: "status" | "alert" }) {
  const tone = props.tone ?? "manual";
  return (
    <div className={`flex gap-2 rounded-[4px] border px-3 py-2 text-[12px] leading-[1.5] ${CALLOUT[tone]}`} role={props.role ?? "status"}>
      <span aria-hidden="true" className="mt-[1px] inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-current text-[10px] font-bold">
        {CALLOUT_GLYPH[tone]}
      </span>
      <div className="min-w-0">
        {props.title ? <p className="font-semibold">{props.title}</p> : null}
        {props.children ? <div className={props.title ? "mt-0.5 opacity-95" : ""}>{props.children}</div> : null}
      </div>
    </div>
  );
}

/** Groups several notices so they do not push the content off screen. All text stays in the DOM. */
export function Notices(props: { title: string; items: Array<{ key: string; tone?: Tone; content: ReactNode }>; open?: boolean }) {
  if (props.items.length === 0) return null;
  const worst = props.items.some((item) => item.tone === "fail") ? "fail" : "manual";
  return (
    <details className={`rounded-[4px] border ${CALLOUT[worst]}`} open={props.open} data-testid="notices">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-[12px] font-semibold">
        <span>
          <span aria-hidden="true">! </span>
          {props.title} ({props.items.length})
        </span>
        <span className="text-[11px] font-normal opacity-80">Show or hide</span>
      </summary>
      <ul className="space-y-1.5 border-t border-current/20 px-3 py-2 text-[12px] leading-[1.5]">
        {props.items.map((item) => (
          <li key={item.key} className="flex gap-2">
            <span aria-hidden="true">•</span>
            <span className="min-w-0">{item.content}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function EmptyState(props: { title: string; reason: string; action?: ReactNode }) {
  return (
    <div className="rounded-[4px] border border-dashed border-line-strong bg-surface-2 px-4 py-6 text-center text-[12.5px]">
      <p className="font-semibold text-ink">{props.title}</p>
      <p className="mx-auto mt-1 max-w-xl text-muted">{props.reason}</p>
      {props.action ? <div className="mt-3 flex justify-center">{typeof props.action === "string" ? <p>{props.action}</p> : props.action}</div> : null}
    </div>
  );
}

export function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading" className="space-y-2">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="h-8 animate-pulse rounded-[3px] bg-[var(--gtf-neutral-bg)]" />
      ))}
    </div>
  );
}

/* --------------------------------------------------------------- Inputs */

const FIELD = "h-8 rounded-[4px] border border-line-strong bg-surface px-2 text-[12.5px] text-ink placeholder:text-muted hover:border-[var(--gtf-muted)] disabled:opacity-50";

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, id, className, ...rest } = props;
  const fieldId = id ?? label.replace(/\s+/g, "-").toLowerCase();
  return (
    <label className={`flex min-w-0 flex-col gap-1 text-[11px] font-medium text-muted ${className ?? ""}`} htmlFor={fieldId}>
      {label}
      <input id={fieldId} {...rest} className={FIELD} />
    </label>
  );
}

export function SelectInput(props: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string; children: ReactNode }) {
  const { label, id, children, className, ...rest } = props;
  const fieldId = id ?? label.replace(/\s+/g, "-").toLowerCase();
  return (
    <label className={`flex min-w-0 flex-col gap-1 text-[11px] font-medium text-muted ${className ?? ""}`} htmlFor={fieldId}>
      {label}
      <select id={fieldId} {...rest} className={FIELD}>
        {children}
      </select>
    </label>
  );
}

export function Checkbox(props: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-[12.5px]">
      <input type="checkbox" className="accent-[var(--gtf-accent)]" checked={props.checked} onChange={(event) => props.onChange(event.target.checked)} />
      {props.label}
    </label>
  );
}

export function Switch(props: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={props.checked}
      onClick={() => props.onChange(!props.checked)}
      className="flex items-center gap-2 rounded-[4px] border border-line bg-surface px-2 py-1 text-[12px]"
    >
      <span className={`relative inline-block h-3.5 w-6 rounded-full border border-line-strong ${props.checked ? "bg-[var(--gtf-accent)]" : "bg-canvas"}`}>
        <span className={`absolute top-[1px] h-2.5 w-2.5 rounded-full bg-[var(--gtf-ink)] ${props.checked ? "left-[11px]" : "left-[1px]"}`} />
      </span>
      {props.label}
    </button>
  );
}

/** Mutually exclusive choice rendered as pressed buttons (keeps aria-pressed semantics). */
export function Segmented<T extends string>(props: { label: string; value: T; options: Array<{ value: T; label: string; title?: string }>; onChange: (value: T) => void }) {
  return (
    <div role="group" aria-label={props.label} className="inline-flex overflow-hidden rounded-[4px] border border-line-strong">
      {props.options.map((option) => (
        <button
          key={option.value}
          type="button"
          title={option.title}
          aria-pressed={props.value === option.value}
          onClick={() => props.onChange(option.value)}
          className={`h-7 min-w-8 border-r border-line-strong px-2.5 text-[12px] font-medium last:border-r-0 ${
            props.value === option.value ? "bg-[var(--gtf-accent)] text-[var(--gtf-accent-ink)]" : "bg-surface text-ink-2 hover:bg-surface-2"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/* --------------------------------------------------------------- Tables */

export interface Column<T> {
  key: string;
  header: string;
  sortValue?: (row: T) => string | number;
  render: (row: T) => ReactNode;
  numeric?: boolean;
}

export function DataTable<T extends { id: string }>(props: {
  caption: string;
  rows: T[];
  columns: Column<T>[];
  onActivate?: (row: T) => void;
  selectedId?: string | null;
}) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [cursor, setCursor] = useState(0);
  const rows = [...props.rows];
  if (sort) {
    const column = props.columns.find((item) => item.key === sort.key);
    if (column?.sortValue) {
      rows.sort((a, b) => {
        const left = column.sortValue?.(a) ?? "";
        const right = column.sortValue?.(b) ?? "";
        if (left < right) return -1 * sort.dir;
        if (left > right) return 1 * sort.dir;
        return 0;
      });
    }
  }
  return (
    <div className="scroll-thin overflow-auto rounded-[4px] border border-line">
      <table className="gtf-table w-full border-collapse text-left text-[12px]">
        <caption className="sr-only">{props.caption}</caption>
        <thead className="sticky top-0 z-[1] bg-surface-2">
          <tr>
            {props.columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                aria-sort={sort?.key === column.key ? (sort.dir === 1 ? "ascending" : "descending") : undefined}
                className={`border-b border-line px-2.5 py-2 ${column.numeric ? "text-right" : ""}`}
              >
                {column.sortValue ? (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-left hover:text-ink"
                    onClick={() =>
                      setSort((current) =>
                        current?.key === column.key ? { key: column.key, dir: current.dir === 1 ? -1 : 1 } : { key: column.key, dir: 1 },
                      )
                    }
                  >
                    {column.header}
                    <span aria-hidden="true" className="text-[9px]">
                      {sort?.key === column.key ? (sort.dir === 1 ? "▲" : "▼") : "↕"}
                    </span>
                  </button>
                ) : (
                  column.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody
          tabIndex={0}
          aria-label={props.caption}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setCursor((value) => Math.min(rows.length - 1, value + 1));
            }
            if (event.key === "ArrowUp") {
              event.preventDefault();
              setCursor((value) => Math.max(0, value - 1));
            }
            if (event.key === "Enter") {
              const row = rows[cursor];
              if (row) props.onActivate?.(row);
            }
          }}
        >
          {rows.map((row, index) => {
            const selected = props.selectedId ? props.selectedId === row.id : index === cursor;
            return (
              <tr
                key={row.id}
                aria-selected={selected}
                className={selected ? "bg-[var(--gtf-selection)]" : undefined}
                style={{ height: 34 }}
              >
                {props.columns.map((column) => (
                  <td key={column.key} className={`border-b border-line px-2.5 ${column.numeric ? "num" : ""}`}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export { statusRank };

/* -------------------------------------------------------------- Dialogs */

export function Dialog(props: {
  title: string;
  body: string;
  confirm: string;
  onConfirm: () => void;
  onClose: () => void;
  children?: ReactNode;
}) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.querySelector<HTMLElement>("button, input, select, textarea")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") props.onClose();
      if (event.key === "Tab" && panel.current) {
        const items = [...panel.current.querySelectorAll<HTMLElement>("button, input, select, textarea, [href]")].filter((item) => !item.hasAttribute("disabled"));
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [props.onClose]);
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" role="presentation">
      <div ref={panel} role="dialog" aria-modal="true" aria-labelledby="dialog-title" className="w-full max-w-md rounded-[6px] border border-line bg-elevated p-4 shadow-[var(--gtf-shadow-lg)]">
        <h2 id="dialog-title" className="text-[15px] font-semibold">
          {props.title}
        </h2>
        <p className="mt-2 text-[12.5px] text-muted">{props.body}</p>
        {props.children ? <div className="mt-3">{props.children}</div> : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" onClick={props.onClose}>
            Cancel
          </Button>
          <Button type="button" variant="primary" onClick={props.onConfirm}>
            {props.confirm}
          </Button>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------- Buttons */

type ButtonVariant = "default" | "primary" | "ghost" | "danger";

const BUTTON: Record<ButtonVariant, string> = {
  default: "border-line-strong bg-surface text-ink hover:bg-surface-2",
  primary: "border-transparent bg-[var(--gtf-accent)] text-[var(--gtf-accent-ink)] hover:opacity-90",
  ghost: "border-transparent bg-transparent text-ink-2 hover:bg-surface-2",
  danger: "border-[var(--gtf-fail)]/50 bg-surface text-[var(--gtf-fail)] hover:bg-[var(--gtf-fail-bg)]",
};

export function Button(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: "sm" | "md" }) {
  const { variant = "default", size = "md", className, ...rest } = props;
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-[4px] border font-medium disabled:cursor-not-allowed disabled:opacity-45 aria-pressed:border-[var(--gtf-accent)] aria-pressed:bg-[var(--gtf-accent-bg)] aria-pressed:text-[var(--gtf-accent)] ${
        size === "sm" ? "h-6 px-2 text-[11.5px]" : "h-7.5 px-2.5 text-[12px]"
      } ${BUTTON[variant]} ${className ?? ""}`}
    />
  );
}
