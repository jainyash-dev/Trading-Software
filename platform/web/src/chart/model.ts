import type { Candle, Timeframe, ZoneStatus, ZoneView } from "../types/contracts";

export interface SeriesIssue {
  index: number;
  time: string | null;
  code: "INVALID_TIMESTAMP" | "DUPLICATE_TIMESTAMP" | "OUT_OF_ORDER" | "INVALID_OHLC";
}

export type PreparedSeries =
  | { ok: true; candles: Candle[]; gaps: number }
  | { ok: false; candles: Candle[]; issues: SeriesIssue[] };

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Refuse a series that cannot be drawn honestly. Do not drop or reorder rows. */
export function prepareSeries(input: readonly Candle[]): PreparedSeries {
  const issues: SeriesIssue[] = [];
  const seen = new Set<string>();
  let previous: string | null = null;
  input.forEach((candle, index) => {
    const timeOk = DATE.test(candle.time);
    if (!timeOk) {
      issues.push({ index, time: candle.time, code: "INVALID_TIMESTAMP" });
    } else if (seen.has(candle.time)) {
      issues.push({ index, time: candle.time, code: "DUPLICATE_TIMESTAMP" });
    } else if (previous !== null && candle.time <= previous) {
      issues.push({ index, time: candle.time, code: "OUT_OF_ORDER" });
    }
    if (timeOk) {
      seen.add(candle.time);
      previous = candle.time;
    }
    const prices = [candle.open, candle.high, candle.low, candle.close];
    const volumeOk = candle.volume === null || (Number.isFinite(candle.volume) && candle.volume >= 0);
    const ohlcOk =
      prices.every((value) => Number.isFinite(value)) &&
      candle.high >= candle.low &&
      candle.high >= candle.open &&
      candle.high >= candle.close &&
      candle.low <= candle.open &&
      candle.low <= candle.close &&
      volumeOk;
    if (!ohlcOk) issues.push({ index, time: candle.time, code: "INVALID_OHLC" });
  });
  if (issues.length > 0) return { ok: false, candles: [...input], issues };
  let gaps = 0;
  for (let i = 1; i < input.length; i += 1) {
    const left = input[i - 1];
    const right = input[i];
    if (left && right) {
      const days = (Date.parse(`${right.time}T00:00:00Z`) - Date.parse(`${left.time}T00:00:00Z`)) / 86_400_000;
      if (days > 3) gaps += 1;
    }
  }
  return { ok: true, candles: [...input], gaps };
}

export interface ZoneStyle {
  fill: string | null;
  stroke: string;
  dash: number[];
  freshDemand: boolean;
}

export function zoneStyle(zone: Pick<ZoneView, "side" | "overlayStatus">): ZoneStyle {
  if (zone.side === "supply") {
    return { fill: "rgba(143, 45, 45, 0.12)", stroke: "#8f2d2d", dash: [], freshDemand: false };
  }
  const status: ZoneStatus = zone.overlayStatus;
  if (status === "FRESH") {
    return { fill: "rgba(29, 107, 58, 0.18)", stroke: "#1d6b3a", dash: [], freshDemand: true };
  }
  if (status === "TESTED") {
    return { fill: "rgba(92, 103, 115, 0.12)", stroke: "#5c6773", dash: [4, 3], freshDemand: false };
  }
  if (status === "INVALIDATED") {
    return { fill: null, stroke: "#8f2d2d", dash: [4, 3], freshDemand: false };
  }
  return { fill: "rgba(61, 74, 92, 0.10)", stroke: "#3d4a5c", dash: [1, 3], freshDemand: false };
}

export type DrawingKind = "horizontal" | "trend" | "rectangle" | "text";

export interface DrawingPoint {
  time: string;
  price: number;
}

export type DrawingPersistence = "MEMORY_ONLY" | "PLATFORM_DB";

export interface DrawingRecord {
  drawingId: string;
  symbol: string;
  timeframe: Timeframe;
  asOf: string | null;
  kind: DrawingKind;
  points: DrawingPoint[];
  text: string;
  persistence: DrawingPersistence;
  version: number;
}

export function createDrawing(
  kind: DrawingKind,
  points: DrawingPoint[],
  text: string,
  scope: { symbol: string; timeframe: Timeframe },
): DrawingRecord {
  return {
    drawingId: `mem-${kind}-${points.map((point) => point.time).join("-")}-${points[0]?.price ?? 0}`,
    symbol: scope.symbol,
    timeframe: scope.timeframe,
    asOf: null,
    kind,
    points,
    text,
    persistence: "MEMORY_ONLY",
    version: 1,
  };
}

export function moveDrawing(record: DrawingRecord, deltaPrice: number, deltaTime: string | null): DrawingRecord {
  return {
    ...record,
    version: record.version + 1,
    points: record.points.map((point) => ({
      time: deltaTime ?? point.time,
      price: roundPrice(point.price + deltaPrice),
    })),
  };
}

export function resizeRectangle(record: DrawingRecord, anchor: DrawingPoint, next: DrawingPoint): DrawingRecord {
  if (record.kind !== "rectangle") return record;
  return { ...record, version: record.version + 1, points: [anchor, next] };
}

export interface Pixel {
  x: number;
  y: number;
}

export function distanceToSegment(point: Pixel, start: Pixel, end: Pixel): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = dx * dx + dy * dy;
  if (length === 0) return Math.hypot(point.x - start.x, point.y - start.y);
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / length));
  return Math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy));
}

export function hitRectangle(point: Pixel, a: Pixel, b: Pixel, pad = 6): "body" | "nw" | "ne" | "sw" | "se" | null {
  const left = Math.min(a.x, b.x);
  const right = Math.max(a.x, b.x);
  const top = Math.min(a.y, b.y);
  const bottom = Math.max(a.y, b.y);
  const corners = {
    nw: { x: left, y: top },
    ne: { x: right, y: top },
    sw: { x: left, y: bottom },
    se: { x: right, y: bottom },
  } as const;
  for (const [name, corner] of Object.entries(corners) as [keyof typeof corners, Pixel][]) {
    if (Math.hypot(point.x - corner.x, point.y - corner.y) <= pad) return name;
  }
  if (point.x >= left && point.x <= right && point.y >= top && point.y <= bottom) return "body";
  return null;
}

function roundPrice(value: number): number {
  return Math.round(value * 100) / 100;
}
