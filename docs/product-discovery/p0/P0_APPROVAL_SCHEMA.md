# Nifty 100 approval schema

**Dated 2026-11-11. Engineering decision ED-48. One ledger: `nse/data/universe/nifty100_review.csv`.**

`decision` stays the full membership-row approval (`ACCEPTED` or `REJECTED`). Two columns were added. They are not a second ledger, and an existing `ACCEPTED` is not copied into them.

| Column | Where it is valid | What it grants |
|---|---|---|
| `count_approval` | `exception:` rows only | The derived count on that date passes the count gate |
| `mapping_approval` | `change:` rows only | The symbol and the add or remove direction are recorded |
| `decision` | any row | That row can start or end a verified membership period |

A period is verified only when its source verifies, its start and its end (if any) have `decision` `ACCEPTED` with the same hash, the count gate passes, and the identity check is clear. `count_approval` can pass the count gate when `decision` is blank. `mapping_approval` is never read by that check, so it cannot verify BANKBARODA or CHOLAFIN from 2021-09-30. A count approval does not accept a dummy-seat row. An inferred ISIN is not approved by either scope. A `REJECTED` value, a scope on the wrong kind of row, a missing reviewer, or a bad date approves nothing.

A review file with the original six columns still means what it meant. On an exception row, a legacy `decision` `ACCEPTED` with a blank `count_approval` still passes only the count gate.

The canonical file has the eight-column header. All 271 `decision` values stay blank. The owner token "count decision ACCEPTED" is stored as `count_approval` `APPROVED`. The owner token "mapping decision ACCEPTED" is stored as `mapping_approval` `APPROVED`. Neither value is written into `decision`.

Recorded on 2026-11-11, reviewer `Yash Jain`, and only on these rows:

- 25 `exception:` rows: `count_approval` `APPROVED`.
- 10 `change:E03:` rows: `mapping_approval` `APPROVED`.

The other 246 rows have an empty reviewer, date, notes and both scope columns. The backup of the six-column file is `nse/data/universe/nifty100_review.before-approval-schema-2026-11-11.csv`. Its `row_key` and `row_sha256` values were not changed.

`RecordedOwnerApprovals` in `tests/test_research_membership.py` converts this file. With both groups recorded and every `decision` blank, zero periods verify. BANKBARODA and CHOLAFIN from 2021-09-30 stay unverified. The five dummy symbols stay unverified. A separate test writes `decision` `ACCEPTED` on the BANKBARODA row alone and checks that CHOLAFIN stays unverified.
