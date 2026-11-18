/** Map stored research zone rows into chart overlays. Display only; never scores eligibility. */

import type { Timeframe, ZoneStatus, ZoneView } from "../types/contracts";

export type ZoneVisibility = Record<Timeframe, boolean>;

export const DEFAULT_ZONE_VISIBILITY: ZoneVisibility = { M: true, W: true, D: true };

function asStatus(raw: string): ZoneStatus {
  const value = raw.toUpperCase();
  if (value === "FRESH" || value === "TESTED" || value === "INVALIDATED") {
    return value;
  }
  // BLOCKED and any other code stay unknown for overlay styling; disposition carries the block reason.
  return "UNKNOWN";
}

function asTimeframe(raw: string): Timeframe | null {
  if (raw === "M" || raw === "W" || raw === "D") return raw;
  return null;
}

function pushZone(
  zones: ZoneView[],
  seen: Set<string>,
  symbol: string,
  tf: Timeframe,
  zone: Record<string, unknown>,
  fallbackStatus?: string,
): void {
  const id = String(zone.zone_id || zone.id || "");
  const proximal = Number(zone.proximal);
  const distal = Number(zone.distal);
  if (!id || !Number.isFinite(proximal) || !Number.isFinite(distal)) return;
  const key = `${tf}:${id}`;
  if (seen.has(key)) return;
  seen.add(key);
  const rawStatus = String(zone.overlay_status || fallbackStatus || "UNKNOWN");
  const status = asStatus(rawStatus);
  zones.push({
    source: "engine",
    engineId: id,
    symbol,
    timeframe: tf,
    side: zone.side === "supply" ? "supply" : "demand",
    startTime: String(zone.start_time || zone.created_time || ""),
    createdTime: String(zone.created_time || zone.start_time || ""),
    proximal,
    distal,
    overlayStatus: status,
    label: `${tf} ${id} ${rawStatus}`,
    pattern: zone.pattern ? String(zone.pattern) : undefined,
    engineStatus: zone.engine_status ? String(zone.engine_status) : undefined,
    disposition: zone.disposition ? String(zone.disposition) : undefined,
    testCount: typeof zone.test_count === "number" ? zone.test_count : undefined,
  });
}

/** Consume candidates, fresh_zones, and blocked_zones from a stored symbol payload. */
export function zonesFromStored(
  stored: Record<string, unknown> | null | undefined,
  symbol: string,
  visibility: ZoneVisibility = DEFAULT_ZONE_VISIBILITY,
): ZoneView[] {
  if (!stored) return [];
  const zones: ZoneView[] = [];
  const seen = new Set<string>();

  const candidates = (stored.candidates as Array<Record<string, unknown>> | undefined) || [];
  for (const candidate of candidates) {
    const zone = (candidate.zone || {}) as Record<string, unknown>;
    const tf = asTimeframe(String(candidate.execution_tf || zone.tf || ""));
    if (!tf || !visibility[tf]) continue;
    pushZone(zones, seen, symbol, tf, { ...zone, tf }, String(zone.overlay_status || "UNKNOWN"));
  }

  const fresh = (stored.fresh_zones as Array<Record<string, unknown>> | undefined) || [];
  for (const row of fresh) {
    const tf = asTimeframe(String(row.tf || ""));
    if (!tf || !visibility[tf]) continue;
    // D3: scanner fresh_zones rows are overlay-fresh only (tested/invalidated/unknown never appear).
    // Prefer explicit overlay_status/freshness when present; otherwise FRESH from list contract.
    const explicit = row.overlay_status || row.freshness;
    pushZone(zones, seen, symbol, tf, row, explicit ? String(explicit) : "FRESH");
  }

  const blocked = (stored.blocked_zones as Array<Record<string, unknown>> | undefined) || [];
  for (const row of blocked) {
    const tf = asTimeframe(String(row.tf || ""));
    if (!tf || !visibility[tf]) continue;
    pushZone(zones, seen, symbol, tf, { ...row, disposition: row.disposition }, String(row.overlay_status || "UNKNOWN"));
  }

  return zones;
}
