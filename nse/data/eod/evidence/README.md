# EOD format evidence (B18, ED-20)

Official NSE files kept to verify the two bhavcopy formats and the switch between them.
They are **evidence, not research data**: nothing here is read by a scan, a backtest or
`acquire-plan`. The research dataset is `nse/data/eod/raw/` with `nse/data/eod/manifest.csv`.

| Path | What |
|---|---|
| `samples/` | Nine bhavcopy archives, under the names NSE serves: legacy and UDiFF for 2024-01-20, 2024-03-02, 2024-05-18 and 2024-07-05 (both formats published), and UDiFF for 2024-07-08 (first date after the legacy file was discontinued) |
| `manifest.csv` | One ARCHIVE and one ARCHIVE_MEMBER row per sample, in the EOD manifest format, so `nse_bhavcopy.load(path, "nse/data/eod/evidence/manifest.csv")` verifies size and SHA-256 |
| `circulars/` | NSE/MSD/62424 (binding: the switch dates), 56202 and 54028 (context only) |
| `sources.csv` | Reference, date, file, SHA-256, size, download date and URL for each circular |

Provenance: every file was retrieved by Claude from the URL recorded next to it on
2026-11-09 (`provenance_status` `CLAUDE_FETCHED_OFFICIAL_ARCHIVE_FORMAT_EVIDENCE`). The
2024-07-08 UDiFF archive was fetched twice, independently, and both copies were
byte-identical. Archives and PDFs are git-ignored (`.gitignore`, `/nse/data/**/*.zip`,
`*.pdf`); the CSVs and this README are not. The tests in `tests/test_nse_eod_evidence.py`
skip with a clear reason when the files are absent.

What the samples establish is recorded in `nse/docs/EOD_FORMAT_EVIDENCE.md` section 9.
