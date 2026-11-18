const KEY = "gtf-scan-pending";

export interface PendingScan {
  idempotencyKey: string;
  body: Record<string, unknown>;
  jobId?: string;
}

export function readPendingScan(): PendingScan | null {
  const raw = window.sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PendingScan>;
    if (!parsed || typeof parsed.idempotencyKey !== "string" || !parsed.body || typeof parsed.body !== "object") return null;
    return {
      idempotencyKey: parsed.idempotencyKey,
      body: parsed.body,
      jobId: typeof parsed.jobId === "string" ? parsed.jobId : undefined,
    };
  } catch {
    return null;
  }
}

export function writePendingScan(value: PendingScan): void {
  window.sessionStorage.setItem(KEY, JSON.stringify(value));
}
