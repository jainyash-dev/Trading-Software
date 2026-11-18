const KEY = "gtf-watchlist-pending";

export interface PendingWatchlist {
  idempotencyKey: string;
  name: string;
  symbols: string[];
}

export function readPendingWatchlist(): PendingWatchlist | null {
  const raw = window.sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PendingWatchlist>;
    if (!parsed || typeof parsed.idempotencyKey !== "string" || typeof parsed.name !== "string" || !Array.isArray(parsed.symbols)) {
      return null;
    }
    return { idempotencyKey: parsed.idempotencyKey, name: parsed.name, symbols: parsed.symbols.filter((item) => typeof item === "string") };
  } catch {
    return null;
  }
}

export function writePendingWatchlist(value: PendingWatchlist): void {
  window.sessionStorage.setItem(KEY, JSON.stringify(value));
}

export function clearPendingWatchlist(): void {
  window.sessionStorage.removeItem(KEY);
}
