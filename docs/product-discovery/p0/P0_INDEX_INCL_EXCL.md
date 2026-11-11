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

## Three ISIN breaks stay unresolved

Local corporate-action responses do not name the new ISIN.

| Symbol | Bhavcopy change | ISIN in the saved response | What the response shows | What is missing |
|---|---|---|---|---|
| BAJFINANCE | 2016-09-09, `INE296A01016` then `INE296A01024` | `INE296A01016` only | Bonus 1:1 and face-value split, ex-date 2016-09-08, record date 2016-09-10 | A notice that names `INE296A01024` and the session it takes effect |
| GRASIM | 2016-10-07, `INE047A01013` then `INE047A01021` | `INE047A01013` only | Face-value split, ex-date 2016-10-06, record date 2016-10-08 | A notice that names `INE047A01021` and the session it takes effect |
| YESBANK | 2020-03-16, `INE528G01027` then `INE528G01035` | `INE528G01019` only | 2017 face-value split. No March 2020 event | A notice that names `INE528G01035` on 2020-03-16 |

`EQUITY_L.csv` lists the later GRASIM and YESBANK ISINs as the current equity-list values. It does not date the change. The bhavcopy first-session dates are observations. They are not joined. No inferred ISIN was written.
