# P0 price-gap investigation

**Dated 2026-11-10. Prices were not adjusted, filled, or rewritten.**

Investigation: Price gaps, agent id 24bcf852-93a2-4dab-a68f-729bd1edba58 (read-only). This pass
re-read the corporate-action rows for the two scale events and confirmed that
`marketdata.from_bhavcopy` defaults to series `EQ`. The bhavcopy rows quoted below are
the investigation's extracts. They were not adjusted.

The Priority 03 certification called two multi-month stretches unexplained because an
EQ-only pass saw no EQ row between them. That description remains the historical
finding. Reading the non-EQ rows changes the classification. The older report was not
rewritten.

## 1. Classifications

| Symbol | Dates | Classification | What the raw files show |
|---|---|---|---|
| ADANIPOWER | 2021-06-11 close 148.3 to 2021-09-20 open 96.05 | `REAL_MARKET_MOVE` | 67 normal sessions, all series `BE`, same ISIN `INE814H01011`. Previous-close equals the prior close on every step |
| CGPOWER | 2021-09-15 close 89 to 2022-01-04 open 197 | `REAL_MARKET_MOVE` | 75 held sessions of series `BE`, including the 2021-11-04 Muhurat. Same ISIN `INE067A01029`. Previous-close chains |
| ADANIPOWER | 2025-09-19 close 709.40 to 2025-09-22 open 148.20 | `CORPORATE_ACTION_UNADJUSTED` | Recorded 1:5 face-value split. ISIN changes from `INE814H01011` to `INE814H01029`. Raw prices left on their own scale |
| CROMPGREAV | 2016-03-14 close 155.3 to 2016-03-15 open 53 | `UNRESOLVED` | Scheme of arrangement on the ex-date. No ratio in the file. 2.93 is not an integer split |
| CROMPGREAV to CGPOWER | 2017-03-08 | No price gap | Same ISIN. Open 71.15 versus previous close 70.95. `D51` already joins a verified rename |

`actions.csv` SHA-256 cited by the investigation: `749757252b68f41199f1194278a5d33e6b608253efe5d03a3dd6a8a6be947fa6`. The split row and the scheme row were re-read from that file.

## 2. ADANIPOWER 2025-09-22 split

`actions.csv` stores `SPLIT`, ratio 1:5, ex-date and record date 2025-09-22, subject
"Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", ISIN
`INE814H01011`. The saved response is `raw/ca_ADANIPOWER_2016_2025.json`, SHA-256
`88b21aa668309ebe543cf503548907238df1a35274bb032e864415e02cc858b7`.

Calendar: 2025-09-19 Friday normal, weekend, 2025-09-22 Monday normal.

Raw EQ rows, as extracted:

- 2025-09-19: ISIN `INE814H01011`, open 676.00, high 723.00, low 665.35, close 709.40, previous close 716.10. Archive SHA-256 `082cdbde89ba1bf28633be126645b353c10b0e0e31190e7b43193917b9858d89`.
- 2025-09-22: ISIN `INE814H01029`, open 148.20, high 170.25, low 147.30, close 170.25, previous close 709.40. Archive SHA-256 `317ca34ae71af34a77848368be9b6c54a3e54c8e52763f63c3fa43cd17f3f2f6`.

Arithmetic from those fields:

- Previous close on the ex-date equals the prior close: `709.40 - 709.40 = 0`.
- Open versus that previous close: `148.20 / 709.40 - 1 = -79.1091%`.
- Close versus that previous close: `170.25 / 709.40 - 1 = -76.0008%`.
- Theoretical ex-price at 1:5: `709.40 / 5 = 141.88`. The open is 6.32 above that level.

The ex-date OHLC is on the post-split scale. The previous-close field stays on the
pre-split close. `D50` keeps raw unadjusted OHLC canonical. The identity break is
already in `instrument_records.csv`. A study that pastes the two ISINs onto one price
scale has to exclude any zone or trade that crosses 2025-09-22. The raw file stays
unadjusted.

## 3. The two multi-month EQ holes

### ADANIPOWER, 2021-06-11 to 2021-09-20

The certification's EQ numbers are exact: close 148.3, then open 96.05, 67 sessions
later. EQ-only, `96.05 / 148.3 - 1 = -35.2326%`. The 2021-09-20 previous close is
100.45, which is not the 2021-06-11 EQ close.

The intervening path is 67 series `BE` rows, one per held session, ISIN unchanged.
2021-06-14 BE previous close is 148.3, equal to the prior EQ close. 2021-09-20 EQ
previous close is 100.45, equal to the 2021-09-17 BE close. The largest open versus the
prior close on that path is about `-4.9974%` (2021-07-20 to 2021-07-22). No
corporate-action row in the window. No local circular states why the series became BE.

### CGPOWER, 2021-09-15 to 2022-01-04

EQ-only: close 89, then open 197, `197 / 89 - 1 = +121.3483%`. The 2022-01-04 previous
close is 196.1, equal to the 2022-01-03 BE close, and `197 / 196.1 - 1 = +0.4589%`.
Seventy-five BE rows, including the Muhurat on 2021-11-04. ISIN unchanged. Largest step
about `+4.9940%`. No split, bonus, or rights in the window.

### What the EQ filter does

`from_bhavcopy` defaults to `series="EQ"`. An EQ-only series has a hole across these
stretches and will report `NO_ROW_IN_FILE` and `PREVCLOSE_DISCONTINUITY`. That flag is
the filter. It is not evidence of a split. Filling the hole with BE or BZ prices would
be a new series rule. No owner decision does that.

Other EQ holes found in the same pass, each filled by BE or BZ with previous-close
chained and a largest step of about 5%:

| Symbol | EQ last to EQ next | Sessions between | EQ-only open versus last close | Path |
|---|---|---|---|---|
| ADANIPOWER | 2021-10-21 to 2021-11-01 | 6 | -20.33% | BE |
| ADANIPOWER | 2022-08-24 to 2022-11-28 | 62 normal, plus the 2022-10-24 Muhurat | -16.21% | BE |
| ADANIPOWER | 2022-12-23 to 2023-01-02 | 5 | +15.56% | BE |
| ADANIPOWER | 2023-12-13 to 2024-03-18 | 64 normal, plus 2024-03-02 | +1.05% | BE |
| CGPOWER | 2019-12-24 to 2020-02-13 | 36 | -13.46% | BZ |
| CGPOWER | 2020-09-01 to 2020-09-14 | 8 | +12.44% | BE |
| CGPOWER | 2021-06-08 to 2021-09-13 | 65 | +11.12% | BE |

Adjacent EQ moves beyond 20% with previous-close equal to the prior close, and no
price-scale action on the date, were classified `REAL_MARKET_MOVE`: ADANIPOWER
2018-10-10 and 2020-03-12; CROMPGREAV 2016-02-03; CGPOWER 2019-02-13 and 2019-02-14.
Block (`BL`) rows chain to other block rows and were not treated as EQ scale breaks.

## 4. CROMPGREAV scheme, 2016-03-15

Adjacent normal sessions, all held. The bhavcopy symbol is CROMPGREAV. The action is
stored under CGPOWER because that is the symbol the API was queried with. ISIN on both
is `INE067A01029`.

`actions.csv` line for CGPOWER 2016-03-15: `UNPARSED_PRICE_EVENT`, ratio 0,0, subject
"Scheme Of Arrangement", record date 16-Mar-2016. The investigation reports
`ca_CROMPGREAV_2016_2025.json` as an empty list. The event is on the CGPOWER response
only.

Extracted EQ rows:

- 2016-03-14: open 149, high 160, low 146, close 155.3, previous close 146.4.
- 2016-03-15: open 53, high 53.05, low 40.3, close 44, previous close 155.3.
- 2016-03-16: open 44.8, previous close 44, close 46.85.

`53 / 155.3 - 1 = -65.8725%`. `155.3 / 53 = 2.930189`. Previous close on the 15th equals
the 14th close, and previous close on the 16th equals the 15th close. The drop is one
session. The OHLC on the 15th is ordered. Volume on the 15th is 86,704,206.

The print is a real unadjusted ex-date. The factor is not in the file. `D50` forbids
applying an unverified ratio. Classification stays `UNRESOLVED`.

The 2017-03-08 rename is continuous: CROMPGREAV close 70.95 on 2017-03-07, CGPOWER open
71.15 and previous close 70.95 on 2017-03-08, same ISIN. No second ISIN and no overlap.

## 5. Owner decisions

| ID | Question | Current evidence | Recommendation | If deferred |
|---|---|---|---|---|
| OD-PX-1 | May research candles include BE and BZ rows when EQ is absent? | The trades exist. The series-change reason is not in a local circular. The loader reads EQ only | Leave the EQ filter in place. Treat the stretches as missing EQ sessions. Do not backfill from BE/BZ | The EQ-only `PREVCLOSE_DISCONTINUITY` flags remain. They are not splits |
| OD-PX-2 | What ratio applies to the CROMPGREAV scheme of 2016-03-15? | Subject text only. Ratio fields are 0,0. No scheme document | Keep the raw series. Exclude continuity-sensitive work across that date until a sourced ratio exists | The factor stays unknown. No price is invented |
| OD-PX-3 | ADANIPOWER across 2025-09-22 | 1:5 split and the ISIN change are recorded. Raw OHLC is unadjusted by `D50` | Keep the two ISINs separate. Do not back-adjust | A joined price scale remains invalid |

## 6. What was not done

- No OHLC was interpolated, scaled, or overwritten.
- No BE or BZ row was added to the EQ research series.
- No ratio was written for 2016-03-15.
- `run_all` and a scan were not run.
- Priority 03's "unexplained" sentences were left in place as the record of the EQ-only pass.
- `IMPLEMENTATION_BLOCKERS.md` still lists ADANIPOWER among older ISIN gaps. The later instrument record and this bhavcopy pair treat 2025-09-22 as evidenced. That older paragraph was not rewritten.

## 7. Reconfirmed in the remediation pass

`marketdata.from_bhavcopy` still defaults to `series="EQ"`. No BE or BZ row was added
to that series. The ADANIPOWER 2025-09-22 `ISIN_CHANGE` row is still the split already
recorded, and the two ISINs are not pasted onto one price scale. The CGPOWER 2016-03-15
row is still `UNPARSED_PRICE_EVENT` with ratio 0,0. No ratio was written. The EQ-only
policy is unchanged and remains OD-PX-1.

## 8. Research effect

Raw unadjusted OHLC stays canonical. ADANIPOWER remains two ISINs at 2025-09-22.
CROMPGREAV stays joined to CGPOWER on the verified rename. Continuity-sensitive work
across 2016-03-15 and across 2025-09-22 is excluded until OD-PX-2 is evidenced and
OD-PX-3 is respected. The two multi-month "gaps" are ordinary traded paths on BE, visible
only as holes in an EQ-only series.
