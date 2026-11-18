import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  type IChartApi,
  type IPrimitivePaneRenderer,
  type IPrimitivePaneView,
  type ISeriesPrimitive,
  type SeriesAttachedParameter,
  type Time,
} from "lightweight-charts";
import { generateCandles } from "./fixtures";

export interface BenchRow {
  label: string;
  candles: number;
  overlays: number;
  setDataMs: number;
  frameMs: number;
  panMs: number;
  zoomMs: number;
  resizeMs: number;
  overlayMs: number;
}

export async function runChartBenchmark(host: HTMLElement): Promise<{ rows: BenchRow[]; library: string }> {
  const rows: BenchRow[] = [];
  for (const [label, count, seed] of [
    ["small", 60, 11],
    ["medium", 504, 12],
    ["large", 2520, 13],
  ] as const) {
    const candles = generateCandles(count, seed);
    if (candles.length !== count) throw new Error(`benchmark dropped candles for ${label}`);
    const chart = createChart(host, {
      width: 800,
      height: 420,
      layout: { background: { type: ColorType.Solid, color: "#0c1014" }, textColor: "#9aa6b2", attributionLogo: true },
    });
    const series = chart.addSeries(CandlestickSeries);
    const volume = chart.addSeries(HistogramSeries, { priceScaleId: "volume" });
    const started = performance.now();
    series.setData(candles.map((candle) => ({ time: candle.time, open: candle.open, high: candle.high, low: candle.low, close: candle.close })));
    volume.setData(candles.map((candle) => ({ time: candle.time, value: candle.volume })));
    const setDataMs = performance.now() - started;
    const zones = new BenchZones(candles);
    const overlayStarted = performance.now();
    series.attachPrimitive(zones);
    const overlayMs = performance.now() - overlayStarted + (await nextFrame());
    const frameMs = await nextFrame();
    const panStarted = performance.now();
    chart.timeScale().scrollToPosition(-20, false);
    const panMs = performance.now() - panStarted + (await nextFrame());
    const zoomStarted = performance.now();
    chart.timeScale().setVisibleLogicalRange({ from: 10, to: Math.max(20, count / 2) });
    const zoomMs = performance.now() - zoomStarted + (await nextFrame());
    const resizeStarted = performance.now();
    chart.resize(900, 460);
    const resizeMs = performance.now() - resizeStarted + (await nextFrame());
    rows.push({
      label,
      candles: candles.length,
      overlays: 8,
      setDataMs: round(setDataMs),
      frameMs: round(frameMs),
      panMs: round(panMs),
      zoomMs: round(zoomMs),
      resizeMs: round(resizeMs),
      overlayMs: round(overlayMs),
    });
    chart.remove();
  }
  return { rows, library: "lightweight-charts" };
}

function nextFrame(): Promise<number> {
  const started = performance.now();
  return new Promise((resolve) => {
    requestAnimationFrame(() => resolve(performance.now() - started));
  });
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

export function chartForTest(host: HTMLElement): IChartApi {
  return createChart(host, { width: 400, height: 300 });
}

class BenchZones implements ISeriesPrimitive<Time> {
  private requestUpdate: (() => void) | null = null;
  private readonly view: IPrimitivePaneView;
  constructor(private readonly candles: { time: string; low: number; high: number }[]) {
    if (this.candles.length < 1) throw new Error("benchmark series empty");
    this.view = {
      zOrder: () => "bottom",
      renderer: (): IPrimitivePaneRenderer => ({
        draw: (target) => {
          target.useBitmapCoordinateSpace((scope) => {
            const ctx = scope.context;
            ctx.fillStyle = "rgba(29, 107, 58, 0.18)";
            const width = scope.bitmapSize.width;
            const height = scope.bitmapSize.height;
            for (let i = 0; i < 8; i += 1) {
              ctx.fillRect((width / 8) * i, height * 0.3, width / 10, height * 0.15);
            }
          });
        },
      }),
    };
  }
  attached(param: SeriesAttachedParameter<Time, "Candlestick">): void {
    this.requestUpdate = param.requestUpdate;
    this.requestUpdate();
  }
  paneViews(): readonly IPrimitivePaneView[] {
    return [this.view];
  }
  request(): void {
    this.requestUpdate?.();
  }
}
