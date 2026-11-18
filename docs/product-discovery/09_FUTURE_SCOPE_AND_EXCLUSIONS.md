# Future scope and exclusions

The initial release is the workflow in [08_PRIORITISED_IMPLEMENTATION_ROADMAP.md](08_PRIORITISED_IMPLEMENTATION_ROADMAP.md) phases A-C. This file is what stays out until that workflow is reliable.

## Deliberately not in the initial release

| Item | Capability IDs | Why it stays out |
|---|---|---|
| WIT and any 75-minute or 125-minute opportunity scan | GTF-017, SD-018 | M4b. No intraday data. The scanner already returns `BLOCKED`. The gate branches behind that return are not a reason to enable them |
| Intraday discovery, DIT, HIT | Not mapped as initial capabilities | The rulebook describes them. The product decision excludes them |
| Futures and options | Not mapped | Cash equities only. The risk check rejects derivatives |
| Broker connection and automated orders | EX-002, EX-014 | The owner types the order in Kite. A client would violate D10 and D17 |
| Live quotes and session alerts | EX-007, EX-008 | No approved provider (OQ-1). A quote must never become the research price |
| Paper and shadow book | QR-014, TJ-012 | A second set of caps before the live journal exists will be written into the wrong table |
| Language-model assistant | AI-002, AI-003, AI-006, AI-007 | OQ-2 is open. The deterministic explainer (AI-001) covers the first need |
| Market regime, sector relative strength, volatility tiles | MI-005, MI-007, MI-008, QR-009 | No definition. A tile will be read as a gate |
| Similar historical setups | OI-007 | Implies a validated match. None has been built or tested |
| Partial exits | EX-010 | No owner rule |
| Multi-user accounts, subscriptions, mobile, hosted cloud, sealed auto-update | UX-018 | One owner, one Mac, loopback |
| Scanning every NSE equity | SD-001 is Nifty 100 | Identity and membership evidence does not exist for the full list |
| Membership before 2020-12-31 | DS-008, B11-P | There is no baseline. TD-15 forbids inventing a reverse step |
| A profitability claim | QR-013 | R4 is open, and R4 itself is not a promise of profit |
| Using the legacy `trader-*` pack as this product | None | US day-trading skills. Different market, different rules. Leave the folders in place |

## Allowed later, after the journal works

| Item | Condition |
|---|---|
| Position monitor | A named quote source, labelled, not written into bhavcopy storage, and only for rows already `TRIGGERED` |
| Paper book | Private tables, `book: SIMULATED`, no call into the live `TRIGGERED` insert |
| Assistant | Owner-approved provider, a field allow-list, no write tool, citations, and the app still boots with the provider unset |
| Walk-forward on screen | Manifests exist (TD-4 closed) and the universe review for that window is done |
| Parse cache | Timed against the uncached loader and keyed by hash plus loader version |
| Full listed universe | A membership and identity project of its own |
| WIT | Intraday data, a session design, and tests of the branches that are currently unreachable |

## Do not build these as substitutes

| Tempting substitute | What it would actually do |
|---|---|
| A green `data_ready` flag while B11-R is open | Certify an unreviewed universe |
| Index or breadth numbers from a formula | Invent MI-002 and MI-006 |
| A quality rank on the scanner | Override the gate order the envelope already refused (AR-9) |
| Hardcoded chart zones "until the API is ready" | The fixture path already exists and is labelled. Extending it onto real symbols would forge zones |
| Platform-side monthly trade count | A second cap (PR-011) |
| Reimplementing G0-G8 in TypeScript | A second methodology |
| Calling scan-diff alerts "live monitoring" | EX-008 would look done and would not see the session |
| Promoting `journal_summary` win rate to the analytics page | FR-9.1 forbids presenting that figure as a strategy result |

## Commercial readiness

There is no licensing server, no account system, and no updater. The chart library attribution flag is on. Privacy of the core path is local. Those facts are enough for one owner. They are not a commercial product. Building subscription infrastructure now would add secrets, accounts, and a network dependency the research engine is required to live without.
