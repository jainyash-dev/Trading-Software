import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OpportunitiesPage } from "./OpportunitiesPage";

const navigate = vi.fn();
const request = vi.fn();
const reportFailure = vi.fn();
const noteFixture = vi.fn();

vi.mock("../../state/store", () => ({
  useAppState: () => ({
    connection: "connected",
    queryString: "",
    request,
    reportFailure,
    noteFixture,
    navigate,
    revision: 0,
  }),
}));

describe("OpportunitiesPage", () => {
  beforeEach(() => {
    navigate.mockReset();
    request.mockReset();
    reportFailure.mockReset();
    noteFixture.mockReset();
    request.mockImplementation(async (path: string) => {
      if (path === "/api/v1/opportunities") {
        return {
          ok: true,
          envelope: {
            meta: { fixture: false },
            data: {
              opportunities: [
                {
                  opportunity_id: "opp-1",
                  scan_key: "scan-1",
                  symbol: "AAA",
                  zone_id: "z-1",
                  timeframe: "D",
                  as_of: "2024-01-02",
                  dataset_id: "ds-1",
                  canonical_status: "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
                  workflow_state: "DISCOVERED",
                  source_quality: "EXPLORATORY",
                  fixture: false,
                  allowed_transitions: ["UNDER_REVIEW"],
                  organizational_priority: { score: 25, authoritative: false, disclosure: "desk only" },
                },
              ],
              counts_by_workflow: { DISCOVERED: 1 },
              priority_disclosure: "Organizational priority does not predict returns.",
              limitation: "P0 certification is incomplete.",
              p0_certified_discovery: false,
              authorises_order: false,
            },
          },
        };
      }
      if (path === "/api/v1/scans") {
        return { ok: true, envelope: { meta: { fixture: false }, data: { scans: [] } } };
      }
      if (path === "/api/v1/watchlists") {
        return { ok: true, envelope: { meta: { fixture: false }, data: { watchlists: [] } } };
      }
      return { ok: false, error: { code: "NOT_FOUND", message: "missing", details: {} }, status: 404 };
    });
  });

  it("states that workflow does not change eligibility", async () => {
    render(<OpportunitiesPage />);
    expect(await screen.findByText(/does not change GTF eligibility/i)).toBeTruthy();
    expect(screen.getAllByText(/P0 certification is incomplete/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/does not imply GTF eligibility/i)).toBeTruthy();
  });

  it("opens stock analysis with the P2 URL contract", async () => {
    render(<OpportunitiesPage />);
    const analysis = await screen.findAllByRole("button", { name: "Analysis" });
    fireEvent.click(analysis[0]);
    expect(navigate).toHaveBeenCalledWith("analysis", {
      scan: "scan-1",
      symbol: "AAA",
      as_of: "2024-01-02",
      dataset_id: "ds-1",
      timeframe: "D",
      zone: "z-1",
    });
  });
});
