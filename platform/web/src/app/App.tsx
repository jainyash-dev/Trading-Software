import { useEffect } from "react";
import { runChartBenchmark } from "../chart/benchmark";
import { Shell } from "../layout/Shell";
import { AppStateProvider } from "../state/store";

export function App(props: { fetcher?: typeof fetch }) {
  // The hidden benchmark host is mounted only for ?bench (P10: it caused horizontal scroll on phones).
  const bench = new URLSearchParams(window.location.search).has("bench");
  useEffect(() => {
    if (!bench) return;
    const host = document.getElementById("bench-host");
    const output = document.getElementById("bench-results");
    if (!host || !output) return;
    void runChartBenchmark(host).then((report) => {
      output.textContent = JSON.stringify(report);
    });
  }, [bench]);
  return (
    <AppStateProvider fetcher={props.fetcher}>
      <Shell />
      {bench ? (
        <>
          <div id="bench-host" className="pointer-events-none fixed left-0 top-0 -z-10 h-[420px] w-[800px] opacity-0" />
          <pre id="bench-results" className="sr-only" />
        </>
      ) : null}
    </AppStateProvider>
  );
}
