# NSE CM Bhavcopy Format Evidence (legacy format)

**Project:** NSE GTF Demand & Supply Swing-Trading Research System
**Date:** 2026-10-27
**Blocker:** B18 (NSE CM EOD file formats unconfirmed). **Still open.** On 2026-10-27 the user accepted this two-sample legacy-format evidence **with the limitations in section 7**; acceptance does not close B18.
**Project status:** Phase 1 in progress; external validation pending.
**Scope:**
- The legacy capital-market bhavcopy (`cmDDMMMYYYYbhav.csv.zip`), for two trade dates: 2022-01-03 and 2023-12-29.
- UDiFF (reported to be used from 2024-07-08; that date is unverified) is **not** covered and remains unverified.
- No loader, parsing rule or trading logic is adopted here. This document records evidence only.

The hash manifest is `nse/data/eod/manifest.csv`. The raw files stay local in `nse/data/eod/raw/`, which `.gitignore` excludes.

---

## 1. Provenance

| Archive | Source page | Download date | Status |
|---|---|---|---|
| `cm03JAN2022bhav.csv.zip` | Official NSE website (exact page not supplied) | 2026-10-27 | **User-confirmed** (2026-10-27); not independently authenticated |
| `cm29DEC2023bhav.csv.zip` | Official NSE website (exact page not supplied) | 2026-10-27 | **User-confirmed** (2026-10-27); not independently authenticated |
| `cm03JAN2022bhav.csv`, `cm29DEC2023bhav.csv` (standalone copies) | Extracted/copied from the matching archive above | Not downloaded separately; derived from the archives downloaded 2026-10-27 | **User-confirmed** copies of the archive members; byte-identical to them (section 4) |

- **User-confirmed provenance.** On 2026-10-27 the user confirmed that both archives were downloaded from the official NSE website on 2026-10-27. That confirmation is recorded as given. The exact page or URL was not supplied, and nothing was invented. The confirmation covers the archives, and so their members.
- **Not independently authenticated.** Nothing here proves the files were issued by NSE. The files carry no download-source metadata: macOS records only a generic `com.apple.provenance` attribute, with no `kMDItemWhereFroms` and no quarantine record. No cross-check against an independent source (such as a TradingView export) has been made yet.
- **The standalone CSVs are copies, not separate downloads.** The user confirmed that `cm03JAN2022bhav.csv` and `cm29DEC2023bhav.csv` were extracted or copied from the two archives above. They were placed in the folder first and the archives were added later. Section 4 shows each copy is byte-identical to its archive member, which is consistent with that statement.

**Method:**
- Every file was read-only. Python ran in isolated mode (`python3 -I`) from a script kept outside the repository.
- The archives were read in memory with the standard `zipfile` module. Nothing was extracted to disk, renamed or re-saved.
- File sizes, hashes and modification times were unchanged after inspection.

## 2. Archives

| Archive | Size (bytes) | SHA-256 | Valid zip | CRC check | Members | Comment / extra fields |
|---|---|---|---|---|---|---|
| `cm03JAN2022bhav.csv.zip` | 83,368 | `3dd80fd92447a313fc50dec9fac8021013b4037717fdbba8f6c3a4700b2b7e5a` | Yes | All members OK | 1 | None / none |
| `cm29DEC2023bhav.csv.zip` | 99,885 | `ba5c7e44708ea3df65a022cdf842eb3fd341421bbf4498c0ea06b3843f8a7cc3` | Yes | All members OK | 1 | None / none |

## 3. Archive members

| Archive | Member | Size (bytes) | Compressed | Method | CRC-32 | Stored timestamp | SHA-256 |
|---|---|---|---|---|---|---|---|
| `cm03JAN2022bhav.csv.zip` | `cm03JAN2022bhav.csv` | 207,607 | 83,216 | 8 (deflate) | `47057811` | 2022-01-03 17:32:14 | `733c764ff287409ea4f4c1ecf6d887379def744d51fb6d3a9cb2137edcf2f1f7` |
| `cm29DEC2023bhav.csv.zip` | `cm29DEC2023bhav.csv` | 247,868 | 99,733 | 8 (deflate) | `72cef229` | 2023-12-29 17:32:22 | `3508952f8f39599b868befc28977cde1b0e8e6f4b38510d6f1eb0967864f746b` |

- Each member's path is a plain file name: no directory part, no absolute path, no `..`.
- The member name is the archive name without `.zip`. This is verified for these two archives only.
- **The stored timestamp is not evidence of the session close.** It is the zip entry's timestamp only and does not establish the 15:30 close assumed for daily candles (audit L7).

## 4. Standalone copies match the archive members

| Standalone file | Size (bytes) | SHA-256 | Identical to archive member |
|---|---|---|---|
| `cm03JAN2022bhav.csv` | 207,607 | `733c764ff287409ea4f4c1ecf6d887379def744d51fb6d3a9cb2137edcf2f1f7` | **Yes**: byte-for-byte equal to the member of `cm03JAN2022bhav.csv.zip` |
| `cm29DEC2023bhav.csv` | 247,868 | `3508952f8f39599b868befc28977cde1b0e8e6f4b38510d6f1eb0967864f746b` | **Yes**: byte-for-byte equal to the member of `cm29DEC2023bhav.csv.zip` |

Every structural finding in section 5 therefore applies equally to the archive members.

## 5. Verified CSV structure (both dates)

| Property | 2022-01-03 | 2023-12-29 |
|---|---|---|
| Encoding | ASCII only (valid UTF-8); no BOM | Same |
| Line endings | LF only (2,228 lines); final newline present | LF only (2,648 lines); final newline present |
| Delimiter / quoting | Comma; no quote characters in the file | Same |
| Data rows | 2,227; every row has 14 fields | 2,647; every row has 14 fields |
| Date column | `TIMESTAMP`, one value: `03-JAN-2022` | `TIMESTAMP`, one value: `29-DEC-2023` |
| Date format | `DD-MMM-YYYY`, upper-case month | Same |
| Filename date = data date | Yes | Yes |
| Time of day in data | None | None |

**Header line (byte-identical in both files):**
```
SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,
```
The trailing comma creates a 14th, unnamed column. It is empty in every row of both files.

**Number formats (both files):**
- `OPEN`, `HIGH`, `LOW`, `CLOSE`, `LAST`, `PREVCLOSE` and `TOTTRDVAL` are plain decimals with 0, 1 or 2 decimal places and trailing zeros trimmed (e.g. `1899`, `1542.9`).
- `TOTTRDQTY` and `TOTALTRADES` are whole numbers.
- No blank values (other than the 14th column), no thousands separators, no negative numbers.

**Integrity observations (both files):**
- No duplicate `(SYMBOL, SERIES)` pair.
- Every `ISIN` is 12 characters starting `IN`.
- No row has a low above its open or close, or a high below them.

**Series values:**
- **2022-01-03:** 69 distinct, including EQ 1,666, BE 210, SM 73, GB 47, BZ 39 and GS 14.
- **2023-12-29:** 81 distinct, including EQ 1,799, BE 300, SM 190, GB 52, GS 36, TB 28, ST 23 and BZ 19.
- Both dates also contain N*, Y* and Z* codes.

The two dates differ only in which series appear and in row counts. Header, column order, encoding, line endings and date format are identical.

**Representative rows (verbatim):**
```
INFY,EQ,1887.75,1914.05,1887.75,1898.45,1899,1887.75,3329616,6342326137.5,03-JAN-2022,128107,INE009A01021,
1018GS2026,GS,95.05,95.05,95.05,95.05,95.05,100,10,950.5,03-JAN-2022,1,IN0020010081,
INFY,EQ,1541.05,1559.45,1540,1542.9,1542.65,1562.65,4388990,6779338989.4,29-DEC-2023,218692,INE009A01021,
182D040124,TB,99.9,99.9,99.9,99.9,99.9,99.75,2000,199800,29-DEC-2023,1,IN002023Y144,
```

## 6. Required-field mapping (`DATA_REQUIREMENTS.md` §2.2)

| Required field | Column | Evidence |
|---|---|---|
| Trade date | `TIMESTAMP` | `DD-MMM-YYYY`; matches the filename date |
| Symbol | `SYMBOL` | Present in every row |
| Series (only `EQ` used) | `SERIES` | `EQ` present on both dates |
| ISIN | `ISIN` | Present in every row |
| Open, high, low, close | `OPEN`, `HIGH`, `LOW`, `CLOSE` | Present, numeric |
| Traded quantity | `TOTTRDQTY` | Present, whole numbers |
| *Wanted:* previous close | `PREVCLOSE` | Present |
| *Wanted:* number of trades | `TOTALTRADES` | Present |
| Not required | `LAST`, `TOTTRDVAL`, unnamed 14th column | Present |

No required field is missing on either date.

## 7. Limitations and open questions

1. **Provenance is user-confirmed, not authenticated.** The source (official NSE website) and download date (2026-10-27) rest on the user's confirmation. The exact page or URL was not supplied. The standalone CSV copies are user-confirmed extractions of the archives, and their bytes match the archive members.
2. **Authenticity not established.** The content is consistent with the NSE capital-market daily equity bhavcopy, but this is not proven. No independent cross-check has been made (H2).
3. **Series meanings unverified.**
   - The meaning of BE, BZ, SM, ST, GB, GS, TB and the N*, Y* and Z* codes is not stated in the files and needs NSE documentation.
   - Using only `EQ` rows is already decided (`DATA_REQUIREMENTS.md` §2.2).
   - **Risk:** if a stock in the universe trades in another series on some day, an EQ-only filter would make that day look missing. A future loader should report such a stock-date rather than drop it silently.
4. **Session close unverified (audit L7).** The data has no time of day. The 15:30 close remains an assumption. The zip timestamps (about 17:32) do not establish it.
5. **Two dates only: continuity is not proven.** Two samples do not prove that the format is the same on every trading day of 2022-2023. Matching files at both ends of the window make a change less likely, but do not rule it out. A future loader should check every file's header against section 5 rather than assume it.
6. **Muhurat session not sampled.** No file for 24 Oct 2022 was provided, so whether one exists, and how a Muhurat session appears, is unknown.
7. **UDiFF not covered.** The UDiFF format and its reported 2024-07-08 start date both remain unverified. Verifying them is a separate, later task.
8. **Prices are unadjusted (B7).** The files contain no corporate-action adjustment; `PREVCLOSE` may later help detect unadjusted gaps.
9. **The manifest is hand-prepared.** `DATA_REQUIREMENTS.md` §2.3 expects a loader to write the manifest. This one was prepared from the inspection; no loader exists.

## 8. B18 status

- **Verified (two dates):** archive names, sizes and hashes; member listing; byte-identity of the standalone copies; the full CSV structure; the mapping of every required field.
- **User-confirmed, not independently verified:** the archives' source and download date, and that the standalone CSVs were extracted or copied from them.
- **Not verified:** authenticity (no independent cross-check, e.g. against TradingView: B8, B10), series meanings, the session close, format continuity across the rest of 2022-2023, the Muhurat session, price adjustment (B7), UDiFF and its start date.
- **User acceptance (2026-10-27):** the user accepted this two-sample legacy-format evidence with the limitations in section 7.
- **B18 stays open.** Acceptance covers this evidence only; it does not establish format continuity across the window or anything about UDiFF. Building a loader needs separate approval (D31).
