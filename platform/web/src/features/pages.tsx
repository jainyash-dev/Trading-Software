import { Page, Skeleton } from "../design/components";
import { AnalysisPage, BacktestPage, JournalPage, PlansPage, PortfolioPage, ReportsPage, SettingsPage } from "./workflow/WorkflowPages";
import { OverviewPage } from "./overview/OverviewPage";
import { OpportunitiesPage } from "./opportunities/OpportunitiesPage";
import { ScannerPage } from "./scanner/ScannerPage";
import { WatchlistsPage } from "./watchlists/WatchlistsPage";
import { ScanHistoryPage } from "./history/ScanHistoryPage";
import { RiskPage } from "./risk/RiskPage";
import { AssistantPage } from "./assistant/AssistantPage";
import { DataHealthPage } from "./system/DataHealthPage";
import { JobsPage } from "./system/JobsPage";
import { AnalyticsPage, PaperPage } from "./capability/CapabilityPage";
import type { RouteId } from "../navigation/routes";
import { useAppState } from "../state/store";

export function Screen({ route }: { route: RouteId }) {
  const app = useAppState();
  if (app.connection === "loading") {
    return (
      <Page title="Loading" description="Checking the local API.">
        <Skeleton />
      </Page>
    );
  }
  switch (route) {
    case "overview":
      return <OverviewPage />;
    case "watchlists":
      return <WatchlistsPage />;
    case "analysis":
      return <AnalysisPage />;
    case "scanner":
      return <ScannerPage />;
    case "opportunities":
      return <OpportunitiesPage />;
    case "history":
      return <ScanHistoryPage />;
    case "plans":
      return <PlansPage />;
    case "portfolio":
      return <PortfolioPage />;
    case "risk":
      return <RiskPage />;
    case "journal":
      return <JournalPage />;
    case "backtest":
      return <BacktestPage />;
    case "reports":
      return <ReportsPage />;
    case "assistant":
      return <AssistantPage />;
    case "data":
      return <DataHealthPage />;
    case "jobs":
      return <JobsPage />;
    case "settings":
      return <SettingsPage />;
    case "analytics":
    case "paper":
      return (
        <>
          <p className="border-b border-line bg-surface-2 px-5 py-2 text-[12px] text-muted">This module is not available in the current release.</p>
          {route === "paper" ? <PaperPage /> : <AnalyticsPage />}
        </>
      );
  }
}
