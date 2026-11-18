import { describe, expect, it } from "vitest";
import { readViewQuery } from "./query";
import { parseHash } from "./routes";

describe("hash routing", () => {
  it("keeps the route and the query", () => {
    expect(parseHash("#/scanner?scan=scan-1&symbol=TCS")).toEqual({ route: "scanner", query: "scan=scan-1&symbol=TCS" });
    expect(parseHash("#/watchlists")).toEqual({ route: "watchlists", query: "" });
    expect(parseHash("#/missing")).toEqual({ route: "overview", query: "" });
    expect(parseHash("#/%E0%A4%A")).toEqual({ route: "overview", query: "" });
  });

  it("drops invalid query tokens and keeps a later query", () => {
    expect(readViewQuery("scan=scan-1&symbol=TCS&zone=Z1&noise=1")).toMatchObject({
      scan: "scan-1",
      symbol: "TCS",
      zone: "Z1",
      timeframe: "",
      ignored: ["noise"],
      rejected: [],
    });
    expect(readViewQuery("scan=scan-1&symbol=TCS&timeframe=W")).toMatchObject({ timeframe: "W" });
    expect(readViewQuery("timeframe=Q").rejected).toContain("timeframe");
    const bad = readViewQuery("scan=bad scan&symbol=TCS");
    expect(bad.scan).toBe("");
    expect(bad.rejected).toContain("scan");
    expect(bad.symbol).toBe("TCS");
  });
});
