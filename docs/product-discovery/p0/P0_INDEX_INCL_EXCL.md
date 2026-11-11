# IndexInclExcl.xls is not a Nifty 100 baseline

Parsed 2026-11-11 from `nse/data/universe/evidence/baseline/IndexInclExcl.xls`.

| Fact | Value |
|---|---|
| SHA-256 | `8869bb7c4df67403131a494a8cc65509e80828f9438bc150b506cdbf55378046` |
| Size | 820,736 bytes |
| Recorded URL | `https://archives.nseindia.com/content/indices/IndexInclExcl.xls` |
| Downloaded | 2026-11-09 |
| File metadata | Created 2011-01-27. Last saved 2020-09-22. Author field: Hrishikesh Chincholikar |
| Reader | `nse.research.index_incl_excl.inspect` |

The workbook has 37 index sheets. The Nifty 100 sheet has four columns: Index Name, Event Date, Scrip Name, Description. It is an inclusion and exclusion log of company names: 168 inclusions and 168 exclusions. Parsed event dates run from 2003-03-19 through 2020-07-31. There is no ISIN cell and no NSE symbol column.

It does not establish a baseline, because all of the following are missing:

- A list of the members in force on 2020-12-31, or on any earlier date that can be rolled to that date.
- NSE symbols.
- ISINs.
- Any Nifty 100 event on or after 2020-12-31.

Company names are not mapped to tickers. No universe row was written from this file. D59 still starts membership research at 2020-12-31. Dates before that remain candle history, not a survivorship-controlled universe.

## ISIN notices retrieved 2026-11-11

The saved NSE corporate-action responses still do not name these new ISINs. Three exchange circulars were downloaded and read from the files, not from a search snippet. PDFs are local (git-ignored). Hashes:

| File | SHA-256 | URL |
|---|---|---|
| `evidence/identity/isin_notices/msei_bajfinance_4496_2016.pdf` | `11b2a619b064c270d04a3fedc14633317d0a87959a212f98dad5349ad14babc5` | `https://www.msei.in/SX-Content/Circulars/2016/September/Circular-4496.pdf` |
| `evidence/identity/isin_notices/msei_grasim_4581_2016.pdf` | `974296c5ad548d0f69e686af4cdb36d04e2472c7dc486a6ea68144d50ea2511d` | `https://www.msei.in/SX-Content/Circulars/2016/October/Circular-4581.pdf` |
| `evidence/identity/isin_notices/nse_yesbank_cml43833_2020.pdf` | `c8d17de1f2d3e805d0776fc3cfd5d748cabb8a258d57e5eb27abd8138cf808e9` | `https://archives.nseindia.com/content/circulars/INSP43833.pdf` |

BAJFINANCE, MSEI/LIST/4496/2016, 7 September 2016. The page says the ISIN changes with effect from 9 September 2016, from `INE296A01016` to `INE296A01024`, record date 10 September 2016, and also that the new ISIN is effective for trades from the ex-date 8 September 2016. Those are two effective dates. The histories are not joined.

GRASIM, MSEI/LIST/4581/2016, 4 October 2016. The page says the ISIN changes with effect from 7 October 2016, from `INE047A01013` to `INE047A01021`, record date 6 October 2016, and also that the new ISIN is effective for trades from the ex-date 6 October 2016. Those are two effective dates. The histories are not joined. This is a Metropolitan Stock Exchange circular, not an NSE circular.

YESBANK, NSE/CML/43833, 15 March 2020. The circular says dealing is permitted in new ISIN `INE528G01035` from 16 March 2020. It does not print the previous ISIN. That single date matches the first held session of `INE528G01035`. An `ISIN_CHANGE` row was added to `instrument_records.csv`. The previous ISIN closed by that row is the one already active in the records, `INE528G01027`. `EQUITY_L.csv` is still not the evidence for the date.
