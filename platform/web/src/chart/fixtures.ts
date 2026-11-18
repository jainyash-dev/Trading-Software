import type { Candle, GateView, Timeframe, ZoneView } from "../types/contracts";

export const FIXTURE_SYMBOL = "EXAMPLE";
export const FIXTURE_LABEL = "FIXTURE_NOT_MARKET_DATA";

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function addDays(iso: string, days: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function weekday(iso: string): number {
  return new Date(`${iso}T00:00:00Z`).getUTCDay();
}

/** Synthetic weekday bars. This is not an NSE calendar and not a market price. */
export function generateCandles(count: number, seed: number, start = "2016-01-04"): Candle[] {
  const random = mulberry32(seed);
  const rows: Candle[] = [];
  let cursor = start;
  let price = 100;
  while (rows.length < count) {
    const day = weekday(cursor);
    if (day !== 0 && day !== 6) {
      const move = (random() - 0.48) * 1.6;
      const open = round(price);
      const close = round(Math.max(1, open + move));
      const high = round(Math.max(open, close) + random() * 0.8);
      const low = round(Math.min(open, close) - random() * 0.8);
      const volume = Math.round(1000 + random() * 5000);
      rows.push({ time: cursor, open, high, low, close, volume });
      price = close;
    }
    cursor = addDays(cursor, 1);
  }
  return rows;
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

export interface FixtureBook {
  symbol: typeof FIXTURE_SYMBOL;
  label: typeof FIXTURE_LABEL;
  series: Record<Timeframe, Candle[]>;
  zones: ZoneView[];
  gates: GateView[];
  candidateStatus: "MANUAL_REVIEW";
  limitations: string[];
}

export function fixtureBook(): FixtureBook {
  const daily = generateCandles(2520, 4);
  const weekly = generateCandles(520, 8, "2016-01-08");
  const monthly = generateCandles(120, 12, "2016-01-29");
  const anchor = daily[400];
  const later = daily[430];
  const tested = daily[800];
  const testedEnd = daily[820];
  const invalid = daily[1200];
  const invalidEnd = daily[1210];
  const unknown = daily[1600];
  const unknownEnd = daily[1610];
  const supply = daily[2000];
  const supplyEnd = daily[2020];
  if (!anchor || !later || !tested || !testedEnd || !invalid || !invalidEnd || !unknown || !unknownEnd || !supply || !supplyEnd) {
    throw new Error("fixture series shorter than expected");
  }
  const zones: ZoneView[] = [
    zone("demand-fresh", "demand", "FRESH", anchor, later, 1.2),
    zone("demand-tested", "demand", "TESTED", tested, testedEnd, 1.4),
    zone("demand-invalid", "demand", "INVALIDATED", invalid, invalidEnd, 1.1),
    zone("demand-unknown", "demand", "UNKNOWN", unknown, unknownEnd, 1.3),
    zone("supply-sample", "supply", "FRESH", supply, supplyEnd, 1.5),
  ];
  const gates: GateView[] = [
    { gate: "G0", title: "Data and history readiness", outcome: "MANUAL", reasons: ["UNIVERSE_UNVERIFIED", "CORPORATE_ACTIONS_UNVERIFIED"] },
    { gate: "G1", title: "Fresh unbreached demand", outcome: "NOT_EVALUATED", reasons: ["Supplied by the fixture. Not calculated here."] },
    { gate: "G2", title: "Core score", outcome: "NOT_EVALUATED", reasons: ["Not supplied"] },
    { gate: "G3", title: "Location", outcome: "NOT_EVALUATED", reasons: ["Not supplied"] },
    { gate: "G4", title: "Trend", outcome: "NOT_EVALUATED", reasons: ["Not supplied"] },
    { gate: "G5", title: "Higher-timeframe conflict", outcome: "NOT_EVALUATED", reasons: ["Not supplied"] },
    { gate: "G6", title: "Coinciding", outcome: "NOT_EVALUATED", reasons: ["Not supplied"] },
    { gate: "G7", title: "Trade levels", outcome: "NOT_EVALUATED", reasons: ["Not supplied"] },
    { gate: "G8", title: "Red flags", outcome: "NOT_EVALUATED", reasons: ["Not supplied"] },
  ];
  return {
    symbol: FIXTURE_SYMBOL,
    label: FIXTURE_LABEL,
    series: { D: daily, W: weekly, M: monthly },
    zones,
    gates,
    candidateStatus: "MANUAL_REVIEW",
    limitations: ["UNIVERSE_UNVERIFIED", "CORPORATE_ACTIONS_UNVERIFIED", "ZONE_IDENTITY_UNRESOLVED"],
  };
}

function zone(
  id: string,
  side: ZoneView["side"],
  status: ZoneView["overlayStatus"],
  start: Candle,
  end: Candle,
  width: number,
): ZoneView {
  const mid = (start.low + end.high) / 2;
  const proximal = round(side === "demand" ? mid + width : mid + width);
  const distal = round(side === "demand" ? mid - width : mid + width * 2);
  return {
    source: "engine",
    engineId: id,
    symbol: FIXTURE_SYMBOL,
    timeframe: "D",
    side,
    startTime: start.time,
    createdTime: end.time,
    proximal,
    distal,
    overlayStatus: status,
    label: `${side} ${status}`,
  };
}

let cached: FixtureBook | null = null;

export function sharedFixtureBook(): FixtureBook {
  cached ??= fixtureBook();
  return cached;
}
