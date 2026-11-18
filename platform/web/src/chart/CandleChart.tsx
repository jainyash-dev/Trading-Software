import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineStyle,
  createChart,
  type AutoscaleInfo,
  type IChartApi,
  type IPriceLine,
  type IPrimitivePaneRenderer,
  type IPrimitivePaneView,
  type ISeriesApi,
  type ISeriesPrimitive,
  type Logical,
  type SeriesAttachedParameter,
  type Time,
} from "lightweight-charts";
import { distanceToSegment, hitRectangle, zoneStyle, type DrawingRecord, type Pixel } from "./model";
import { planLineColor, type PlanLine } from "./plans";
import type { Candle, ZoneView } from "../types/contracts";

export interface ChartController {
  fit: () => void;
  zoom: (direction: 1 | -1) => void;
}

interface Props {
  candles: Candle[];
  zones: ZoneView[];
  drawings: DrawingRecord[];
  /** FR-4.9 plan overlay. Recorded plan levels only; labelled PLAN. */
  planLines?: PlanLine[];
  showZones: boolean;
  showVolume: boolean;
  selectedZoneId: string | null;
  selectedDrawingId: string | null;
  onSelectZone: (id: string | null) => void;
  onSelectDrawing: (id: string | null) => void;
  onChangeDrawing: (next: DrawingRecord) => void;
  onController: (controller: ChartController | null) => void;
}

interface Handles {
  apply: () => void;
  chart: IChartApi;
  series: ISeriesApi<"Candlestick">;
  overlay: OverlayPrimitive;
}

export function CandleChart(props: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const legendRef = useRef<HTMLDivElement>(null);
  const propsRef = useRef(props);
  const handlesRef = useRef<Handles | null>(null);
  propsRef.current = props;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let chart: IChartApi;
    try {
      const palette = chartPalette(currentTheme());
      chart = createChart(host, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: palette.background },
        textColor: palette.text,
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: palette.grid },
        horzLines: { color: palette.grid },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: palette.border },
      timeScale: { borderColor: palette.border },
    });
    const series = chart.addSeries(CandlestickSeries, candleColors(palette));
    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const overlay = new OverlayPrimitive();
    series.attachPrimitive(overlay);
    let priceLines: IPriceLine[] = [];

    const apply = () => {
      const current = propsRef.current;
      series.setData(
        current.candles.map((candle) => ({
          time: candle.time,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        })),
      );
      volume.setData(
        current.showVolume
          ? current.candles
              .filter((candle) => candle.volume !== null)
              .map((candle) => ({
                time: candle.time,
                value: candle.volume as number,
                color: candle.close >= candle.open ? chartPalette(currentTheme()).volumeUp : chartPalette(currentTheme()).volumeDown,
              }))
          : [],
      );
      for (const line of priceLines) series.removePriceLine(line);
      priceLines = (current.planLines || []).map((line) =>
        series.createPriceLine({
          price: line.price,
          color: planLineColor(line.kind),
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: line.label,
        }),
      );
      overlay.planPrices = (current.planLines || []).map((line) => line.price);
      overlay.zones = current.showZones ? current.zones : [];
      overlay.drawings = current.drawings;
      overlay.selectedDrawingId = current.selectedDrawingId;
      overlay.selectedZoneId = current.selectedZoneId;
      overlay.request();
    };
    handlesRef.current = { apply, chart, series, overlay };
    apply();
    // P10-2: follow the application theme without recreating the chart.
    const themeObserver = typeof MutationObserver === "function"
      ? new MutationObserver(() => {
          const next = chartPalette(currentTheme());
          chart.applyOptions({
            layout: { background: { type: ColorType.Solid, color: next.background }, textColor: next.text },
            grid: { vertLines: { color: next.grid }, horzLines: { color: next.grid } },
            rightPriceScale: { borderColor: next.border },
            timeScale: { borderColor: next.border },
          });
          series.applyOptions(candleColors(next));
          apply();
        })
      : null;
    themeObserver?.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    chart.timeScale().fitContent();

    const project = (time: string, price: number): Pixel | null => {
      const x = chart.timeScale().timeToCoordinate(time as Time);
      const y = series.priceToCoordinate(price);
      if (x === null || y === null) return null;
      return { x, y };
    };

    chart.subscribeCrosshairMove((param) => {
      const legend = legendRef.current;
      if (!legend) return;
      const time = typeof param.time === "string" ? param.time : null;
      const candle = time ? propsRef.current.candles.find((row) => row.time === time) : undefined;
      legend.textContent = candle
        ? `${candle.time}  O ${candle.open.toFixed(2)}  H ${candle.high.toFixed(2)}  L ${candle.low.toFixed(2)}  C ${candle.close.toFixed(2)}  V ${candle.volume === null ? "unavailable" : candle.volume}`
        : "Crosshair";
    });
    chart.subscribeClick((param) => {
      if (!param.point) return;
      const current = propsRef.current;
      const zone = current.showZones ? hitZone(current.zones, param.point, project) : null;
      if (zone) {
        current.onSelectZone(zone.engineId);
        current.onSelectDrawing(null);
        return;
      }
      const drawing = hitDrawing(current.drawings, param.point, project);
      current.onSelectZone(null);
      current.onSelectDrawing(drawing?.drawingId ?? null);
    });

    let drag: { id: string; lastY: number; moved: DrawingRecord } | null = null;
    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0) return;
      const point = localPoint(host, event);
      const drawing = hitDrawing(propsRef.current.drawings, point, project);
      if (!drawing || drawing.kind === "text") return;
      drag = { id: drawing.drawingId, lastY: point.y, moved: drawing };
      event.preventDefault();
      event.stopPropagation();
    };
    const onPointerMove = (event: PointerEvent) => {
      if (!drag) return;
      const point = localPoint(host, event);
      const price = series.coordinateToPrice(point.y);
      const previous = series.coordinateToPrice(drag.lastY);
      if (price === null || previous === null) return;
      const delta = price - previous;
      drag.lastY = point.y;
      drag.moved = {
        ...drag.moved,
        version: drag.moved.version + 1,
        points: drag.moved.points.map((item) => ({
          ...item,
          price: Math.round((item.price + delta) * 100) / 100,
        })),
      };
      overlay.drawings = propsRef.current.drawings.map((row) => (row.drawingId === drag?.id ? drag.moved : row));
      overlay.request();
    };
    const onPointerUp = () => {
      if (!drag) return;
      propsRef.current.onChangeDrawing(drag.moved);
      drag = null;
    };
    host.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);

    props.onController({
      fit: () => chart.timeScale().fitContent(),
      zoom: (direction) => zoom(chart, direction),
    });

    return () => {
      propsRef.current.onController(null);
      host.removeEventListener("pointerdown", onPointerDown, true);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      handlesRef.current = null;
      themeObserver?.disconnect();
      chart.remove();
    };
    } catch {
      if (legendRef.current) legendRef.current.textContent = "Chart did not start in this environment";
      return;
    }
  }, []);

  useEffect(() => {
    handlesRef.current?.apply();
  }, [props.candles, props.zones, props.drawings, props.planLines, props.showZones, props.showVolume, props.selectedDrawingId, props.selectedZoneId]);

  return (
    <div className="relative h-full min-h-[420px] bg-chart">
      <div ref={legendRef} className="tabular absolute left-2 top-2 z-10 text-[11px] text-muted">
        Crosshair
      </div>
      <div ref={hostRef} className="h-full min-h-[420px]" data-testid="candle-chart" />
    </div>
  );
}

function zoom(chart: IChartApi, direction: 1 | -1) {
  const range = chart.timeScale().getVisibleLogicalRange();
  if (!range) return;
  const span = Number(range.to) - Number(range.from);
  const next = direction > 0 ? span * 0.8 : span * 1.25;
  const mid = (Number(range.from) + Number(range.to)) / 2;
  chart.timeScale().setVisibleLogicalRange({ from: mid - next / 2, to: mid + next / 2 });
}

function localPoint(host: HTMLElement, event: PointerEvent): Pixel {
  const rect = host.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function hitZone(zones: ZoneView[], point: Pixel, project: (time: string, price: number) => Pixel | null): ZoneView | null {
  for (const zone of [...zones].reverse()) {
    const a = project(zone.startTime, zone.proximal);
    const b = project(zone.createdTime, zone.distal);
    if (!a || !b) continue;
    if (hitRectangle(point, a, b, 4)) return zone;
  }
  return null;
}

function hitDrawing(
  drawings: DrawingRecord[],
  point: Pixel,
  project: (time: string, price: number) => Pixel | null,
): DrawingRecord | null {
  for (const drawing of [...drawings].reverse()) {
    const pixels = drawing.points.map((item) => project(item.time, item.price));
    if (pixels.some((pixel) => pixel === null)) continue;
    const [first, second] = pixels;
    if (!first) continue;
    if (drawing.kind === "horizontal" && Math.abs(point.y - first.y) <= 6) return drawing;
    if (drawing.kind === "text" && Math.hypot(point.x - first.x, point.y - first.y) <= 12) return drawing;
    if (drawing.kind === "trend" && second && distanceToSegment(point, first, second) <= 6) return drawing;
    if (drawing.kind === "rectangle" && second && hitRectangle(point, first, second)) return drawing;
  }
  return null;
}

class OverlayPrimitive implements ISeriesPrimitive<Time> {
  zones: ZoneView[] = [];
  drawings: DrawingRecord[] = [];
  planPrices: number[] = [];
  selectedDrawingId: string | null = null;
  selectedZoneId: string | null = null;
  private chart: IChartApi | null = null;
  private series: ISeriesApi<"Candlestick"> | null = null;
  private requestUpdate: (() => void) | null = null;
  private readonly view: OverlayView;

  constructor() {
    this.view = new OverlayView(this);
  }

  attached(param: SeriesAttachedParameter<Time, "Candlestick">): void {
    this.chart = param.chart;
    this.series = param.series;
    this.requestUpdate = param.requestUpdate;
  }

  detached(): void {
    this.chart = null;
    this.series = null;
    this.requestUpdate = null;
  }

  request(): void {
    this.requestUpdate?.();
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this.view];
  }

  autoscaleInfo(_start: Logical, _end: Logical): AutoscaleInfo | null {
    const prices = [
      ...this.zones.flatMap((zone) => [zone.proximal, zone.distal]),
      ...this.drawings.flatMap((drawing) => drawing.points.map((point) => point.price)),
      ...this.planPrices,
    ];
    if (prices.length === 0) return null;
    return { priceRange: { minValue: Math.min(...prices), maxValue: Math.max(...prices) } };
  }

  project(time: string, price: number): Pixel | null {
    if (!this.chart || !this.series) return null;
    const x = this.chart.timeScale().timeToCoordinate(time as Time);
    const y = this.series.priceToCoordinate(price);
    if (x === null || y === null) return null;
    return { x, y };
  }
}

class OverlayView implements IPrimitivePaneView {
  constructor(private readonly primitive: OverlayPrimitive) {}

  zOrder(): "bottom" {
    return "bottom";
  }

  renderer(): IPrimitivePaneRenderer {
    return {
      draw: (target) => {
        target.useBitmapCoordinateSpace((scope) => {
          const ctx = scope.context;
          const horizontal = scope.horizontalPixelRatio;
          const vertical = scope.verticalPixelRatio;
          for (const zone of this.primitive.zones) {
            const a = this.primitive.project(zone.startTime, zone.proximal);
            const b = this.primitive.project(zone.createdTime, zone.distal);
            if (!a || !b) continue;
            const style = zoneStyle(zone);
            const left = Math.min(a.x, b.x) * horizontal;
            const right = Math.max(a.x, b.x) * horizontal;
            const top = Math.min(a.y, b.y) * vertical;
            const bottom = Math.max(a.y, b.y) * vertical;
            if (style.fill) {
              ctx.fillStyle = style.fill;
              ctx.fillRect(left, top, Math.max(1, right - left), Math.max(1, bottom - top));
            }
            ctx.save();
            ctx.strokeStyle = zone.engineId === this.primitive.selectedZoneId ? chartPalette(currentTheme()).selected : style.stroke;
            ctx.lineWidth = vertical;
            ctx.setLineDash(style.dash.map((part) => part * horizontal));
            ctx.strokeRect(left, top, Math.max(1, right - left), Math.max(1, bottom - top));
            ctx.restore();
            ctx.fillStyle = style.stroke;
            ctx.font = `${11 * vertical}px sans-serif`;
            ctx.fillText(zone.label, left + 4 * horizontal, top + 12 * vertical);
          }
          for (const drawing of this.primitive.drawings) {
            const pixels = drawing.points
              .map((point) => this.primitive.project(point.time, point.price))
              .filter((pixel): pixel is Pixel => pixel !== null);
            const first = pixels[0];
            const second = pixels[1];
            if (!first) continue;
            const selected = drawing.drawingId === this.primitive.selectedDrawingId;
            ctx.save();
            ctx.strokeStyle = "#6b4c9a";
            ctx.fillStyle = selected ? "rgba(107, 76, 154, 0.28)" : "rgba(107, 76, 154, 0.08)";
            ctx.lineWidth = (selected ? 2 : 1) * vertical;
            if (drawing.kind === "horizontal") {
              ctx.beginPath();
              ctx.moveTo(0, first.y * vertical);
              ctx.lineTo(scope.bitmapSize.width, first.y * vertical);
              ctx.stroke();
            } else if (drawing.kind === "trend" && second) {
              ctx.beginPath();
              ctx.moveTo(first.x * horizontal, first.y * vertical);
              ctx.lineTo(second.x * horizontal, second.y * vertical);
              ctx.stroke();
            } else if (drawing.kind === "rectangle" && second) {
              const left = Math.min(first.x, second.x) * horizontal;
              const right = Math.max(first.x, second.x) * horizontal;
              const top = Math.min(first.y, second.y) * vertical;
              const bottom = Math.max(first.y, second.y) * vertical;
              ctx.fillRect(left, top, right - left, bottom - top);
              ctx.strokeRect(left, top, right - left, bottom - top);
            } else if (drawing.kind === "text") {
              ctx.fillStyle = "#6b4c9a";
              ctx.font = `${12 * vertical}px sans-serif`;
              ctx.fillText(drawing.text || "Note", first.x * horizontal, first.y * vertical);
            }
            ctx.restore();
          }
        });
      },
    };
  }
}

interface ChartPalette {
  background: string;
  text: string;
  grid: string;
  border: string;
  up: string;
  down: string;
  volumeUp: string;
  volumeDown: string;
  selected: string;
}

function currentTheme(): "dark" | "light" {
  return typeof document !== "undefined" && document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

/** Price-direction colours only. Zone and plan colours keep the specification table. */
export function chartPalette(theme: "dark" | "light"): ChartPalette {
  if (theme === "light") {
    return {
      background: "#fbfcfd",
      text: "#4b5664",
      grid: "#eef1f4",
      border: "#cfd6de",
      up: "#1d6b3a",
      down: "#8f2d2d",
      volumeUp: "rgba(29, 107, 58, 0.35)",
      volumeDown: "rgba(143, 45, 45, 0.35)",
      selected: "#141a21",
    };
  }
  return {
    background: "#0c1015",
    text: "#9aa6b2",
    grid: "#18202a",
    border: "#2a3340",
    up: "#3c9b62",
    down: "#c25b5b",
    volumeUp: "rgba(60, 155, 98, 0.4)",
    volumeDown: "rgba(194, 91, 91, 0.4)",
    selected: "#e6ebf1",
  };
}

function candleColors(palette: ChartPalette) {
  return {
    upColor: palette.up,
    downColor: palette.down,
    borderUpColor: palette.up,
    borderDownColor: palette.down,
    wickUpColor: palette.up,
    wickDownColor: palette.down,
  };
}
