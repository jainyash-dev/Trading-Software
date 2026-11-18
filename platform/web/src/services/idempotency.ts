export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `key-${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

export function stable(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return `[${value.map((item) => stable(item)).join(",")}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stable(record[key])}`)
    .join(",")}}`;
}

export function isoDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const day = value.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null;
}

export function jobPollInterval(): number {
  const override = window.sessionStorage.getItem("gtf-poll-ms");
  if (!override) return 2000;
  const parsed = Number(override);
  return Number.isFinite(parsed) && parsed >= 15 ? parsed : 2000;
}
