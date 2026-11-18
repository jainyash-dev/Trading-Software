import { describe, expect, it } from "vitest";
import { statusCount } from "./model";

describe("overview counts", () => {
  it("keeps a missing scan distinct from a zero count", () => {
    expect(statusCount(null, "DATA_INSUFFICIENT")).toBeNull();
    expect(statusCount(undefined, "DATA_INSUFFICIENT")).toBeNull();
    expect(statusCount({ candidate_status: { REJECTED: 2 } }, "DATA_INSUFFICIENT")).toBeNull();
    expect(statusCount({ candidate_status: { DATA_INSUFFICIENT: 0 } }, "DATA_INSUFFICIENT")).toBe(0);
  });
});
