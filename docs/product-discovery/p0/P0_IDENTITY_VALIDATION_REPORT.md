# P0 identity validation

**Dated 2026-11-10. Status: not resolved. Histories were not joined.**

Investigation: Identity breaks, agent id f42ffce6-ea90-4568-a0e5-214984f41e8d (read-only).
This pass re-counted `instrument_records.csv`: BAJFINANCE 3 rows, GRASIM 2, YESBANK 3.
The file has 219 records. SHA-256 `af269f76722dd34702d208e49dfcb5395e1381c191b9dd55f274e06ba7a11dd1`.
`identity_report.json` SHA-256 `67287f82a90b0f1a2339b555c2f8604af823b4b1a386e410eacc423f89a57aba`.

Of 30 ISIN transitions in the member bhavcopies, 27 are evidenced and 3 are not. The
unevidenced three are only these names. `D56` and `ED-37` leave an unevidenced change
unjoined. `ED-29` does not join OHLC across an ISIN change even when a later change is
evidenced. No price was adjusted.

## 1. What the code does

`instruments.lineage` joins a predecessor only through a verified symbol change with a
continuous ISIN. These three symbols have no symbol-change row, so each lineage is the
symbol alone.

`isin_consistency` emits `ISIN_CHANGED_WITHOUT_RECORD` when the ISIN changes and no
`ISIN_CHANGE` row covers the first session of the new ISIN. `scanner.scan_symbol`
returns `DATA_INSUFFICIENT` and no candidates when that error is known at `as_of`.
Earlier `as_of` dates do not see it. The error stays on every later `as_of`.

`resolve` is a different path. While the old listing is still open and a second listing
has started, it returns `UNKNOWN_INSTRUMENT`. A later `RESOLVED` result does not clear
the scan block.

## 2. BAJFINANCE

| Span | ISIN | Sessions |
|---|---|---|
| 2016-01-01 .. 2016-09-08 | INE296A01016 | 170 EQ |
| 2016-09-09 .. 2025-06-13 | INE296A01024 | 2,171 EQ |
| 2025-06-16 .. 2025-12-31 | INE296A01032 | 137 EQ |

`EQUITY_L.csv` lists the current ISIN `INE296A01032` only. `symbolchange.csv` records
`BAJAUTOFIN` to `BAJFINANCE` on 29-SEP-2010 and has no ISIN. No held row prints
`BAJAUTOFIN`.

The saved corporate-action file (`fa813f2c4be5198ed04e2e886d30035b0983fad11b2436051d4e4fa60806817b`)
prints `isin` `INE296A01016` on every row, including the 2025 events. The 2016 subject
is a bonus 1:1 and a face-value split from Rs 10 to Rs 2, ex-date 08-Sep-2016, record
date 10-Sep-2016 (a Saturday). `actions.csv` stores both parts on ex-date 2016-09-08.

Boundary prints:

- 2016-09-08, old ISIN: close 1162.8, previous close 11393.3.
- 2016-09-09, new ISIN: previous close 1162.8, equal to the prior close.
- 2025-06-13, `INE296A01024`: close 9331.00.
- 2025-06-16, `INE296A01032`: open 956, close 938.00, previous close 9331.00.

The 2025 bonus and split have ex-date and record date 16-Jun-2025, so an `ISIN_CHANGE`
row exists for that date under `ED-37`. The JSON still does not name `INE296A01024` or
`INE296A01032`. The 2016 ex-date is the last old-ISIN session, and the record date is
the Saturday after the ISIN changed. That match was withdrawn in `ED-37`. Calling
2016-09-09 the effective date of `INE296A01024` is an inference, not an established date.

`isin_consistency` reports one error: 2016-09-09 `ISIN_CHANGED_WITHOUT_RECORD`. It is
present on every later `as_of`, including 2025-06-16. `resolve` is `UNKNOWN_INSTRUMENT`
from 2016-09-09 through 2025-06-13, then `RESOLVED` on `INE296A01032` from 2025-06-16.
That resolved result does not lift the scan block. The reported canonical id on
2025-06-16 is `ISIN:INE296A01024`, and the lineage walk does not reach `INE296A01016`.

**Recommendation:** split the identity. Do not accept OHLC continuity across 2016-09-09.
Do not treat the 2025 date match as closing the 2016 gap.

## 3. GRASIM

| Span | ISIN | Sessions |
|---|---|---|
| 2016-01-01 .. 2016-10-06 | INE047A01013 | 189 EQ |
| 2016-10-07 .. 2025-12-31 | INE047A01021 | 2,289 EQ |

There is no GRASIM row in `symbolchange.csv` and no `ISIN_CHANGE` record. `EQUITY_L.csv`
lists `INE047A01021` with a listing date of 10-MAY-1995. The live note on the
`INE047A01021` listing says the ISIN is not in `EQUITY_L.csv`. The file does contain
that ISIN. The note is the template written when the current-list row was replaced and
rebuilt. The 1995 date belongs to the current snapshot, not to a point-in-time start of
`INE047A01013`.

The saved response (`b2e768964bb6086b716ee4f551a2240e8329431435c289723a608de6b6ccb642`)
prints `isin` `INE047A01013` on every row. The split subject is "Face Value Split From
Rs 10 To Re 2", ex-date 06-Oct-2016, record date 08-Oct-2016 (Saturday). The response
never prints `INE047A01021`.

Boundary prints:

- 2016-10-06, old ISIN: close 1009.2, previous close 4933.55.
- 2016-10-07, new ISIN: previous close 1009.2, equal to the prior close.

A scheme of arrangement on 19-Jul-2017 is an `UNPARSED_PRICE_EVENT`. The EQ ISIN does
not change on that date.

The one error is 2016-10-07 `ISIN_CHANGED_WITHOUT_RECORD`, present through 2025-12-31.
`resolve` is `UNKNOWN_INSTRUMENT` from 2016-10-07 onward. The Nifty 100 period from
2020-12-31 records the same finding.

**Recommendation:** split the identity. Do not accept continuity across 2016-10-07. The
2017 scheme does not identify the 2016 ISIN change.

## 4. YESBANK

| Span | ISIN | Sessions |
|---|---|---|
| 2016-01-01 .. 2017-09-21 | INE528G01019 | 427 EQ |
| 2017-09-22 .. 2020-03-13 | INE528G01027 | 611 EQ |
| 2020-03-16 .. 2025-12-31 | INE528G01035 | 1,440 EQ |

The saved response (`6e51a922194bc4bc40581ff3e1f9fdcd9f9d89f3b111fb12751ce95b02e7b1f0`)
has five rows, every `isin` `INE528G01019`: dividends in 2016, 2017, 2018 and 2019, and
a split ex-date 21-Sep-2017, record date 22-Sep-2017. That record date equals the first
`INE528G01027` session, so the 2017 change is evidenced. `ED-29` still does not join the
prices across it. There is no March 2020 event in the response.

Boundary prints:

- 2017-09-21, `INE528G01019`: close 377.05, previous close 1880.1.
- 2017-09-22, `INE528G01027`: previous close 377.05.
- 2020-03-13, `INE528G01027`: close 25.55.
- 2020-03-16, `INE528G01035`: previous close 25.55. No previous-close break.

`EQUITY_L.csv` lists `INE528G01035`. The live note on that listing says the ISIN is not
in `EQUITY_L.csv`. The file does contain it. The same template-note problem as GRASIM.

The one error is 2020-03-16 `ISIN_CHANGED_WITHOUT_RECORD`. `resolve` is
`UNKNOWN_INSTRUMENT` from that date through 2025-12-31. Calling 2020-03-16 a
reconstruction date is not established from these files.

**Recommendation:** do not join across 2020-03-16. Keep `INE528G01035` separate until a
notice names it and the session. Do not stitch the 2017 prices across the evidenced
split.

## 5. Owner decisions

| ID | Question | Recommendation if no new document arrives |
|---|---|---|
| OD-ID-1 | Which document, other than ex-date 08-Sep-2016 and Saturday record date 10-Sep-2016, establishes `INE296A01024` from 2016-09-09? | Leave BAJFINANCE unjoined. Scans from 2016-09-09 stay `DATA_INSUFFICIENT` |
| OD-ID-2 | Which document names `INE047A01021` on a session date? The held split row does not | Leave GRASIM unjoined. Every scan from 2016-10-07 stays `DATA_INSUFFICIENT` |
| OD-ID-3 | Which document states that `INE528G01027` became `INE528G01035`, and on which session? | Leave the 2020 break unjoined. Scans from 2020-03-16 stay `DATA_INSUFFICIENT` |

These are open. Nothing above is an approval. The instrument-record notes were not
rewritten.

## 6. What this does not close

B11-I stays open for these three names. B7 / R-10 still applies: a notice outside the
saved API responses may exist and is not in this repository. The Nifty 100 review rows
for these names are still blank, so the universe periods stay unverified apart from
identity. No identity here is resolved.
