import type { ReactNode } from "react";
import { Limitation } from "../../design/components";
import { presentLimitation } from "../../design/status";
import type { ApiErrorBody } from "../../types/contracts";

export function Section(props: { id?: string; title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section id={props.id} className="panel min-w-0">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-3.5 py-2.5">
        <h2 className="text-[13px] font-semibold">{props.title}</h2>
        {props.action}
      </header>
      <div className="space-y-3 p-3.5">{props.children}</div>
    </section>
  );
}

export function FactGrid(props: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-x-5 gap-y-3 lg:grid-cols-4">{props.children}</div>;
}

export function Fact(props: { label: string; children: ReactNode; testId?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] font-medium text-muted [overflow-wrap:anywhere]">{props.label}</div>
      <div className="mt-0.5 text-[13px] tabular [overflow-wrap:anywhere]" data-testid={props.testId}>
        {props.children}
      </div>
    </div>
  );
}

export function Value({ value }: { value: unknown }) {
  if (typeof value === "boolean") return <span>{value ? "true" : "false"}</span>;
  if (typeof value === "number" && Number.isFinite(value)) return <span className="tabular">{value}</span>;
  if (typeof value === "string" && value.trim()) return <span>{value}</span>;
  return <span className="text-muted">— Unavailable</span>;
}

export function CodeList({ codes }: { codes: string[] | undefined }) {
  if (!codes) return <span className="text-muted">— Unavailable</span>;
  if (codes.length === 0) return <span className="text-[12px]">None returned</span>;
  return (
    <ul className="space-y-1">
      {codes.map((code) => (
        <li key={code}>
          <span className="font-medium">{code}</span>
          <span className="text-muted"> · {presentLimitation(code)}</span>
        </li>
      ))}
    </ul>
  );
}

export function LimitationLine({ code }: { code: string }) {
  return (
    <p>
      <span className="font-medium">{code}</span> <Limitation code={code} />
    </p>
  );
}

export function ErrorLine(props: { error: ApiErrorBody; onRetry?: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-[4px] border border-[var(--gtf-fail)]/50 bg-[var(--gtf-fail-bg)] px-3 py-2 text-[12px] text-[var(--gtf-fail)]" role="status">
      <span>
        {props.error.code}: {props.error.message}
      </span>
      {props.onRetry ? (
        <button type="button" className="rounded-[4px] border border-line-strong bg-surface px-2 py-0.5 text-ink" onClick={props.onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Warning(props: { children: ReactNode }) {
  return (
    <div className="flex gap-2 rounded-[4px] border border-[var(--gtf-manual)]/50 bg-[var(--gtf-manual-bg)] px-3 py-2 text-[12px] leading-[1.5] text-[var(--gtf-manual)]" role="status">
      <span aria-hidden="true" className="font-bold">!</span>
      <div className="min-w-0">{props.children}</div>
    </div>
  );
}

export function JobState({ state }: { state: string | null | undefined }) {
  if (!state) return <span className="text-muted">— Unavailable</span>;
  const tone =
    state === "FAILED" || state === "INTERRUPTED"
      ? "text-[var(--gtf-fail)]"
      : state === "SUCCEEDED_PARTIAL" || state === "CANCELLED"
        ? "text-[var(--gtf-manual)]"
        : "";
  return (
    <span className={`rounded-[3px] border border-line-strong px-1.5 py-0.5 text-[11px] font-medium ${tone}`} data-job-state={state}>
      {state}
    </span>
  );
}

export function Completeness({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="text-muted">— Unavailable</span>;
  const tone = value === "FAILED" ? "text-[var(--gtf-fail)]" : value === "PARTIAL" ? "text-[var(--gtf-manual)]" : "";
  return (
    <span className={`font-medium ${tone}`} data-completeness={value}>
      {value}
    </span>
  );
}
