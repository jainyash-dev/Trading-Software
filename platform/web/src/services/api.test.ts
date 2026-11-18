import { describe, expect, it } from "vitest";
import { parseEnvelope, probeApi, requestHeaders, apiCall } from "./api";

describe("api client", () => {
  it("sends the marker header and does not read a token from storage", () => {
    window.localStorage.setItem("gtf_session", "should-not-be-sent");
    const headers = requestHeaders();
    expect(headers.get("X-GTF-Request")).toBe("1");
    expect(headers.get("Authorization")).toBeNull();
  });

  it("rejects a fixture envelope that omits the required label", () => {
    expect(() => parseEnvelope({ platform_schema: "gtf-platform/1", data: {}, meta: { fixture: true } })).toThrow();
  });

  it("does not replace a failed request with fixture data", async () => {
    const fetcher = (async () => {
      throw new TypeError("offline");
    }) as typeof fetch;
    const probe = await probeApi(fetcher);
    expect(probe.connection).toBe("disconnected");
    expect(probe.health).toBeNull();
    expect(probe.fixtureFromApi).toBe(false);
    expect(probe.error?.code).toBe("DISCONNECTED");
  });

  it("retries once after a 401 and sends an idempotency key only when asked", async () => {
    const calls: string[] = [];
    const fetcher = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push(`${init?.method ?? "GET"} ${url}`);
      const headers = new Headers(init?.headers);
      if (url.endsWith("/scans")) {
        expect(headers.get("Idempotency-Key")).toBe("scan-key");
        return new Response(JSON.stringify({ error: { code: "UNAUTHENTICATED", message: "Session is missing or expired", details: {} } }), { status: 401 });
      }
      if (url.endsWith("/session/bootstrap")) {
        return new Response(
          JSON.stringify({ platform_schema: "gtf-platform/1", data: { authenticated: true, auth: "cookie" }, meta: { fixture: false } }),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify({ platform_schema: "gtf-platform/1", data: { job_id: "job-1", state: "RUNNING" }, meta: { fixture: false } }),
        { status: 202 },
      );
    }) as typeof fetch;
    const first = await apiCall(fetcher, "/api/v1/scans", { method: "POST", body: { mode: "MANUAL" }, idempotencyKey: "scan-key" });
    expect(first.ok).toBe(false);
    expect(calls).toEqual(["POST /api/v1/scans", "POST /api/v1/session/bootstrap", "POST /api/v1/scans"]);
  });
});
