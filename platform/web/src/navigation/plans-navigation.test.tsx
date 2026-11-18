import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../app/App";
import { createPlatform } from "../test/platformFetch";

describe("plan address", () => {
  it("replaces the plan fields when the hash query changes and drops an invalid token", async () => {
    window.location.hash = "#/plans?scan=scan-1&symbol=TCS&zone=Z1";
    render(<App fetcher={createPlatform().fetcher} />);
    expect(await screen.findByLabelText("Scan")).toHaveValue("scan-1");
    expect(screen.getByLabelText("Symbol")).toHaveValue("TCS");
    expect(screen.getByLabelText("Zone")).toHaveValue("Z1");
    window.location.hash = "#/plans?scan=scan-2&symbol=bad%20symbol&zone=Z9";
    expect(await screen.findByDisplayValue("scan-2")).toBeInTheDocument();
    expect(screen.getByLabelText("Symbol")).toHaveValue("");
    expect(screen.getByLabelText("Zone")).toHaveValue("Z9");
    expect(screen.getByText(/Part of the address was ignored/)).toBeInTheDocument();
  });
});
