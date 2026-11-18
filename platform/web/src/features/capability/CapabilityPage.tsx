import type { ReactNode } from "react";
import { Button, Page, Panel, ProvenanceBadge } from "../../design/components";
import type { RouteId } from "../../navigation/routes";
import { useAppState } from "../../state/store";

/**
 * Honest capability-status page for a product area without a backend (P10 section 5.2).
 * It explains the intended purpose and what blocks it. It never renders sample results.
 */
export function CapabilityPage(props: {
  title: string;
  eyebrow: string;
  description: string;
  purpose: string;
  blockers: Array<{ label: string; detail: string }>;
  available: Array<{ label: string; route: RouteId; detail: string }>;
  children?: ReactNode;
}) {
  const app = useAppState();
  return (
    <Page title={props.title} eyebrow={props.eyebrow} description={props.description} meta={<ProvenanceBadge kind="NOT_IMPLEMENTED" />}>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Panel title="What this screen is for">
          <p className="text-[12.5px] leading-[1.6] text-ink-2">{props.purpose}</p>
          {props.children}
        </Panel>
        <Panel title="Why it is not available">
          <ul className="space-y-2.5 text-[12.5px]">
            {props.blockers.map((item) => (
              <li key={item.label}>
                <p className="font-medium">{item.label}</p>
                <p className="text-muted">{item.detail}</p>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      {props.available.length ? (
        <Panel title="What you can use today">
          <ul className="divide-y divide-line">
            {props.available.map((item) => (
              <li key={item.route} className="flex flex-wrap items-center justify-between gap-3 py-2 text-[12.5px]">
                <span className="min-w-0">
                  <span className="font-medium">{item.label}</span>
                  <span className="block text-muted">{item.detail}</span>
                </span>
                <Button type="button" onClick={() => app.navigate(item.route)}>
                  Open {item.label}
                </Button>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </Page>
  );
}

export function PaperPage() {
  return (
    <CapabilityPage
      title="SIMULATED shadow / paper"
      eyebrow="Intelligence"
      description="Simulated data would stay on this screen. It is never the live journal."
      purpose="A simulated book stepped forward after each close: run assumptions, simulated orders and a link to a backtest manifest for comparison. Simulated fills would carry the SIMULATED label and never enter the live journal or the live caps."
      blockers={[
        { label: "TJ-012 paper book", detail: "Owner-deferred in P6. No simulator loop exists in the platform API." },
        { label: "Validated scanner", detail: "PRODUCT_MASTER_STATUS P22: a paper loop depends on a validated scanner and certified history (P0)." },
      ]}
      available={[
        { label: "Trading Journal", route: "journal", detail: "Canonical record of owner-typed fills. Not simulated." },
        { label: "Backtesting", route: "backtest", detail: "Labelled historical study on owner-supplied costs. Not performance evidence." },
      ]}
    >
      <p className="mt-3 text-[12px] text-muted">No paper run. The simulator is not started. No fill is implied.</p>
    </CapabilityPage>
  );
}

export function AnalyticsPage() {
  return (
    <CapabilityPage
      title="Strategy Analytics"
      eyebrow="Intelligence"
      description="Statistics for a cited backtest manifest. No figure is shown without a manifest, a defined execution model and a real dataset."
      purpose="Sample size and evidence label first, then the figures that exist for a cited run manifest, then a caution for small samples. Walk-forward results without a manifest would be shown as incomplete. Missing months are never filled with zero returns."
      blockers={[
        { label: "No analytics API", detail: "The platform exposes POST /api/v1/backtests only. There is no run list, manifest store or analytics route." },
        { label: "No certified history", detail: "P0 certification is incomplete (certified_p0_data is false). Master prompt section 13 forbids win rate, expectancy or drawdown figures without a real dataset and execution model." },
        { label: "Execution model", detail: "B9 / B12 owner inputs (buffer tiers, Kite/GTT baselines, tariff schedule) are required before a study can be quoted." },
      ]}
      available={[
        { label: "Backtesting", route: "backtest", detail: "Run a labelled study. The result is arithmetic on research signals, not evidence." },
        { label: "Trading Journal", route: "journal", detail: "Descriptive journal summary (JOURNAL_DESCRIPTIVE), not strategy performance." },
      ]}
    />
  );
}
