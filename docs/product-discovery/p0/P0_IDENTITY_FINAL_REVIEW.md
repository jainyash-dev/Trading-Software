# P0 identity final review (V3)

**Date:** 2026-11-15. **No identity record was changed** (`instrument_records.csv` SHA-256 `f7ce39b0...` before and after). Row list: `P0_IDENTITY_BLOCKERS_V3.csv`.

## 1. Live identity state (isolated build F, builder 1.6.0)

`RESOLVED` 121,323; `UNKNOWN_INSTRUMENT` **2,455** = BAJFINANCE 1,098 + GRASIM 1,234 + five dummy seats 123.

## 2. Exceptions

| Symbol | ISIN | Dates | Conflict | Documents | Dimensions affected | What would resolve it |
|---|---|---|---|---|---|---|
| BAJFINANCE | INE296A01024 | 2020-12-31..2025-06-13 (1,098) | Old ISIN INE296A01016 LISTING record never ends, so two ISINs claim the symbol | MSEI/LIST/4496/2016; **NSE/CML/33154** (held, `ba3f3210...`): ISIN changed w.e.f. 2016-09-09, new ISIN effective for trades from ex-date 2016-09-08; bhavcopies: old ISIN last 2016-09-08, new first 2016-09-09 | identity; membership (baseline row deferred) | **Owner decision only.** D67: Option 1 KEEP_UNJOINED. The evidence now held would support Option 2 or 3 if the owner revisits |
| GRASIM | INE047A01021 | 2020-12-31..2025-12-31 (1,234) | Same pattern with INE047A01013 | MSEI/LIST/4581/2016; **NSE/CML/33327** (held, `b9529033...`): w.e.f. 2016-10-07; trades from ex-date 2016-10-06; bhavcopies agree | identity; membership | Same; D67 Option 1 |
| DUMMYREL / DUMMYITC / DUMMYSIEMS / DUMMYTATAM / DUMMYHDLVR | as printed by NSE Indices (taken from upstream rows) | 21 / 17 / 49 / 18 / 18 dates | Dummy index seats, not securities | NSE Indices press releases | identity, EQ (no row), membership | OD-MEM-2/3 accounting rule (owner). Never an invented ISIN |

BAJFINANCE from 2025-06-16 (INE296A01032, 136 dates) resolves (ED-37 record). Its membership row stays deferred.

## 3. Optional rows (D67 Q4: deferred)

JIOFIN, ITCHOTELS, ENRIN, TMCV: membership evidence is sufficient (Batch 11). Identity is UNKNOWN at the dummy-to-listed transition and EQ is BE-only while a member. They are kept separate; nothing was written.

## 4. Statement

No transition date was inferred, no history was joined, and no listing end was written.
