/**
 * Display formatting only (P10-2). These helpers never derive a financial value; they
 * format what the API returned. A value that is not a finite number returns null so the
 * caller renders the Unavailable state instead of a zero.
 */

export function toNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

const INR = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const PLAIN = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 4 });
const QTY = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** Rupee amount with Indian digit grouping. Precision is two decimals (display only). */
export function formatInr(value: unknown): string | null {
  const number = toNumber(value);
  if (number === null) return null;
  const sign = number < 0 ? "−" : "";
  return `${sign}₹${INR.format(Math.abs(number))}`;
}

/** A price as returned, grouped, without currency symbol and without rounding beyond 4 dp. */
export function formatPrice(value: unknown): string | null {
  const number = toNumber(value);
  if (number === null) return null;
  return PLAIN.format(number);
}

export function formatQuantity(value: unknown): string | null {
  const number = toNumber(value);
  if (number === null) return null;
  return QTY.format(number);
}

export function formatPercent(value: unknown, digits = 2): string | null {
  const number = toNumber(value);
  if (number === null) return null;
  return `${number.toFixed(digits)}%`;
}

/** Paise integer to rupees, display only. */
export function formatPaise(value: unknown): string | null {
  const number = toNumber(value);
  if (number === null) return null;
  return formatInr(number / 100);
}

/** ISO date or timestamp shown as YYYY-MM-DD (and HH:MM when a time is present). */
export function formatDate(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const match = /^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?/.exec(value);
  if (!match) return value;
  return match[2] ? `${match[1]} ${match[2]}` : match[1];
}

export function text(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value.trim() ? value : null;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : null;
  if (typeof value === "boolean") return value ? "true" : "false";
  return null;
}
