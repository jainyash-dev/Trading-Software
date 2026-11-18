#!/usr/bin/env python3
"""Loader for the legacy NSE capital-market bhavcopy, from local files only. Standard
library only.

Reads exactly the format recorded in nse/docs/EOD_FORMAT_EVIDENCE.md (blocker B18): an
archive `cmDDMMMYYYYbhav.csv.zip` holding one member `cmDDMMMYYYYbhav.csv`, or that CSV
on its own. The format is verified for 2022-01-03 and 2023-12-29 only, so every file is
checked against that evidence rather than assumed to match it. Anything else is refused.

Rules:
  - The header must be exactly LEGACY_HEADER, including the trailing unnamed column.
  - ASCII, LF line endings, a final newline, no BOM and no quote characters, as in the
    evidence. Any other encoding or line ending is refused, not converted.
  - Every row has 14 fields and an empty 14th. SYMBOL and SERIES are non-empty.
    TIMESTAMP is DD-MMM-YYYY and equals the date in the file name. Prices are plain
    non-negative decimals; OPEN, HIGH, LOW and CLOSE are above zero; LOW <= OPEN,
    CLOSE <= HIGH. TOTTRDQTY and TOTALTRADES are whole numbers. ISIN is IN + 10
    letters or digits.
  - A repeated (SYMBOL, SERIES) in one file, or two files for one trade date, is refused.
  - Any failure refuses the whole file (a BhavcopyError naming the line). Nothing is
    skipped, repaired, filled in or inferred, and no missing session is invented.
    One exception, isolated by series (ED-30): a row of an uppercase series code other
    than EQ that fails a value check (RowValueError: prices, OHLC order, quantities, ISIN) is
    rejected and listed in rejected_rows with its line and reason, and the file is kept.
    Official files carry such rows, e.g. the T0 (same-day settlement) series from
    2024-03-28, whose CLOSE is not a T0 trade and can lie outside the T0 high/low, and a
    partly-paid E1 row with ISIN "DUMMY". An invalid EQ row, a row whose series cannot be
    read, a duplicate, and every format-level failure (header, encoding, field count,
    UnsupportedFormatError) still refuse the whole file.
  - Prices are kept exactly as published, as Decimal: unadjusted for corporate actions
    (B7). Nothing here adjusts them.
  - Rows of every series are kept. eq_rows gives the EQ rows (DATA_REQUIREMENTS §2.2);
    non_eq_series counts the others, and non_eq_only_symbols lists symbols that have
    rows on the day but no EQ row (EOD_FORMAT_EVIDENCE §7.3), so an EQ filter can never
    hide them silently.
  - The output is data only: no candles, session times, zones or eligibility. Turning a
    trade date into a candle is a separate step (audit L7: the 15:30 close is assumed).

UDiFF (B18; evidence in nse/docs/EOD_FORMAT_EVIDENCE.md section 9, samples in
nse/data/eod/evidence/): an archive BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip holding
one member of the same name without .zip, or that CSV on its own. Exactly the two header
variants seen in official samples are accepted, each a named schema version; any other
header is refused. Same encoding rules as legacy. Every row: TradDt (YYYY-MM-DD) equals
the file name date and BizDt; Sgmt CM, Src NSE, FinInstrmTp STK and SsnId F1 (the only
values in the samples); the derivative, open-interest and reserved columns empty; the
same price, OHLC, quantity and ISIN checks as legacy. LastPric may be empty (seen only on
debt rows, where legacy prints LAST 0.0): it is kept as None, never filled. Columns
without a legacy counterpart are kept in BhavRow.extra, not dropped.

Source selection (ED-20): NSE/MSD/62424 says the legacy bhavcopy was published "in
parallel along with the new UDiFF format files till July 05, 2024" and discontinued from
July 08, 2024. selected_format(trade_date) is therefore legacy up to 2024-07-05 and UDiFF
from 2024-07-08. load() parses either format for any date (so overlap dates can be
cross-checked with cross_check()); load_many(), which assembles a research dataset,
refuses a file whose format is not the selected one for its date, so the two sources are
never mixed for one date.

Provenance: every result carries the file's name, size and SHA-256 (and the member's,
for an archive). With a manifest (nse/data/eod/manifest.csv) the file must match its
record by name, kind, trade date, size and SHA-256, and that record is attached as
given; a missing or mismatched record refuses the file.
"""

import csv
import datetime
import hashlib
import io
import os
import re
import zipfile
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Dict, List, Optional

LOADER_VERSION = "2.1.0"           # 2.1.0: exact legacy variants LEGACY_13_CRLF(_SHORTDATE), nested member (ED-38); load_many(keep=) (ED-41)
                                    # 2.0.0: UDiFF schema versions and source selection (ED-20)
FORMAT = "NSE_CM_BHAVCOPY_LEGACY"
FORMAT_LEGACY = FORMAT
FORMAT_UDIFF = "NSE_CM_BHAVCOPY_UDIFF"
PRICE_ADJUSTMENT = "NONE"           # as published, unadjusted (B7)

# EOD_FORMAT_EVIDENCE.md section 5; the empty last name is the trailing comma's column
LEGACY_HEADER = ("SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE",
                 "TOTTRDQTY", "TOTTRDVAL", "TIMESTAMP", "TOTALTRADES", "ISIN", "")
LEGACY_SCHEMA = "LEGACY_14"
# MP1 D55 backfill: cm10JUL2017bhav.csv.zip (its member regenerated 2017-07-11) has CRLF line
# endings on every line and a 13-column header without the trailing empty column. Accepted as
# its own schema only when both hold exactly; its rows then pass the same row checks.
LEGACY_CRLF_SCHEMA = "LEGACY_13_CRLF"
LEGACY_CRLF_SHORTDATE_SCHEMA = "LEGACY_13_CRLF_SHORTDATE"
LEGACY_HEADER_13 = LEGACY_HEADER[:-1]

# EOD_FORMAT_EVIDENCE.md section 9. The 34 data columns of every UDiFF CM bhavcopy sample
# (UDIFF_COLUMNS), and the two header spellings around them:
#   UDIFF_2024A  reserved columns Rsvd01..Rsvd04 and a trailing comma in the header only
#                (data rows have 34 fields); samples 2024-01-20, 2024-03-02, 2024-05-18
#   UDIFF_2024B  reserved columns Rsvd1..Rsvd4, no trailing comma; samples 2024-07-05, 2024-07-08
_UDIFF_LEAD = ("TradDt", "BizDt", "Sgmt", "Src", "FinInstrmTp", "FinInstrmId", "ISIN", "TckrSymb",
               "SctySrs", "XpryDt", "FininstrmActlXpryDt", "StrkPric", "OptnTp", "FinInstrmNm", "OpnPric",
               "HghPric", "LwPric", "ClsPric", "LastPric", "PrvsClsgPric", "UndrlygPric", "SttlmPric",
               "OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol", "TtlTrfVal", "TtlNbOfTxsExctd", "SsnId",
               "NewBrdLotQty", "Rmks")
UDIFF_SCHEMAS = {
    "UDIFF_2024A": _UDIFF_LEAD + ("Rsvd01", "Rsvd02", "Rsvd03", "Rsvd04", ""),
    "UDIFF_2024B": _UDIFF_LEAD + ("Rsvd1", "Rsvd2", "Rsvd3", "Rsvd4"),
}
UDIFF_COLUMNS = UDIFF_SCHEMAS["UDIFF_2024B"]
_UDIFF_FIXED = {"Sgmt": "CM", "Src": "NSE", "FinInstrmTp": "STK", "SsnId": "F1"}
_UDIFF_EMPTY = ("XpryDt", "FininstrmActlXpryDt", "StrkPric", "OptnTp", "UndrlygPric", "OpnIntrst",
                "ChngInOpnIntrst", "Rsvd1", "Rsvd2", "Rsvd3", "Rsvd4")
UDIFF_EXTRA = ("FinInstrmId", "FinInstrmNm", "SttlmPric", "NewBrdLotQty", "Rmks")   # no legacy counterpart

# Source selection by trade date (ED-20; NSE/MSD/62424, EOD_FORMAT_EVIDENCE.md section 9)
LEGACY_LAST_TRADE_DATE = datetime.date(2024, 7, 5)
UDIFF_ONLY_FROM = datetime.date(2024, 7, 8)
MANIFEST_COLUMNS = ("file_name", "kind", "parent_archive", "trade_date", "size_bytes",
                    "sha256", "source_page", "downloaded_on", "provenance_status")
MAX_MEMBER_BYTES = 50 * 1024 * 1024  # the verified members are about 0.25 MB

_NAME = re.compile(r"cm(\d{2})([A-Z]{3})(\d{4})bhav\.csv(\.zip)?\Z")
_UDIFF_NAME = re.compile(r"BhavCopy_NSE_CM_0_0_0_(\d{4})(\d{2})(\d{2})_F_0000\.csv(\.zip)?\Z")
_DATE = re.compile(r"(\d{2})-([A-Z]{3})-(\d{4})\Z")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_SERIES = re.compile(r"[A-Z0-9]{1,4}\Z")         # NSE series codes: EQ, BE, T0, E1, N1, GB, SM ...
_DECIMAL = re.compile(r"\d+(\.\d+)?\Z")
_WHOLE = re.compile(r"\d+\Z")
_ISIN = re.compile(r"IN[A-Z0-9]{10}\Z")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"))}
_MONTH_NAMES = {i: m for m, i in _MONTHS.items()}


class BhavcopyError(ValueError):
    """The file is refused; nothing from it is used."""


class UnsupportedFormatError(BhavcopyError):
    """Not the verified legacy format (name, archive layout, encoding or header)."""


class MalformedFileError(BhavcopyError):
    """The legacy format, but the file or a row is invalid."""


class RowValueError(MalformedFileError):
    """A row's VALUE is invalid (price, OHLC order, quantity, ISIN). Only this kind of failure,
    and only on a row of an uppercase non-EQ series code, is isolated instead of refusing the
    file (ED-30). Structural failures (field count, the unnamed 14th column, a date that differs
    from the file name) are MalformedFileError and always refuse the whole file."""


class ProvenanceError(BhavcopyError):
    """The file does not match its manifest record."""


class SourceSelectionError(BhavcopyError):
    """A verified file, but not the format selected for its trade date (ED-20)."""


@dataclass(frozen=True)
class BhavRow:
    symbol: str
    series: str
    trade_date: datetime.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    last: Optional[Decimal]         # None only for a UDiFF row with an empty LastPric
    prev_close: Decimal
    traded_qty: int
    traded_value: Decimal
    total_trades: int
    isin: str
    line: int                       # line number in the CSV (header = 1)
    extra: tuple = ()               # UDiFF columns with no legacy counterpart, (name, text) pairs


@dataclass(frozen=True)
class SourceInfo:
    file_name: str
    kind: str                       # ARCHIVE or CSV
    size_bytes: int
    sha256: str
    member_name: Optional[str]      # archives only
    member_size_bytes: Optional[int]
    member_sha256: Optional[str]


@dataclass
class BhavcopyFile:
    source: SourceInfo
    trade_date: datetime.date
    rows: List[BhavRow]             # every row, every series, in file order (only the kept ones with load_many(keep=))
    series_counts: Dict[str, int]
    non_eq_only_symbols: List[str]  # rows on the day, but no EQ row
    provenance: Optional[Dict[str, str]]   # the manifest record, verbatim
    format: str = FORMAT
    loader_version: str = LOADER_VERSION
    price_adjustment: str = PRICE_ADJUSTMENT
    schema_version: str = LEGACY_SCHEMA
    rejected_rows: tuple = ()       # (line, series, symbol, reason) of isolated non-EQ rows (ED-30)

    @property
    def eq_rows(self):
        return [r for r in self.rows if r.series == "EQ"]

    @property
    def non_eq_series(self):
        return {s: n for s, n in self.series_counts.items() if s != "EQ"}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _short_date(d):
    """The file date as DD-Mon-YY ("13-Jul-20"), the only short form accepted (ED-38)."""
    return "%02d-%s-%02d" % (d.day, _MONTH_NAMES[d.month].title(), d.year % 100)


def _date(text, what):
    m = _DATE.match(text)
    if not m or m.group(2) not in _MONTHS:
        raise MalformedFileError("%s: %r is not DD-MMM-YYYY" % (what, text))
    try:
        return datetime.date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    except ValueError:
        raise MalformedFileError("%s: %r is not a real date" % (what, text))


def selected_format(trade_date):
    """The one source format used for a trade date in a research dataset (ED-20)."""
    return FORMAT_LEGACY if trade_date <= LEGACY_LAST_TRADE_DATE else FORMAT_UDIFF


def name_info(name):
    """(trade date, format) from an official file name; anything else is refused."""
    m = _UDIFF_NAME.match(name)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), FORMAT_UDIFF
        except ValueError:
            raise UnsupportedFormatError("%s: file name date is not a real date" % name)
    return _name_date(name), FORMAT_LEGACY


def official_name(trade_date, fmt=None):
    """The archive name NSE serves for a trade date in a format (default: the selected one)."""
    fmt = fmt or selected_format(trade_date)
    if fmt == FORMAT_UDIFF:
        return "BhavCopy_NSE_CM_0_0_0_%s_F_0000.csv.zip" % trade_date.strftime("%Y%m%d")
    months = sorted(_MONTHS, key=_MONTHS.get)
    return "cm%02d%s%04dbhav.csv.zip" % (trade_date.day, months[trade_date.month - 1], trade_date.year)


ARCHIVE_PATTERNS = ("cm*bhav.csv.zip", "BhavCopy_NSE_CM_0_0_0_*_F_0000.csv.zip")


def archive_paths(folder):
    """Every official bhavcopy archive (both formats) directly in folder, sorted by name.
    Names only: each file is still parsed and checked by load / load_many."""
    import glob
    out = set()
    for pattern in ARCHIVE_PATTERNS:
        out.update(glob.glob(os.path.join(folder, pattern)))
    return sorted(out)


def official_url(trade_date, fmt=None):
    """Where NSE serves that archive (recorded as the manifest source_page; nothing here
    fetches it, D31). URL patterns as recorded in nse/data/eod/evidence/manifest.csv."""
    fmt = fmt or selected_format(trade_date)
    name = official_name(trade_date, fmt)
    if fmt == FORMAT_UDIFF:
        return "https://nsearchives.nseindia.com/content/cm/" + name
    return "https://nsearchives.nseindia.com/content/historical/EQUITIES/%04d/%s/%s" % (
        trade_date.year, name[4:7], name)


def _name_date(name):
    m = _NAME.match(name)
    if not m:
        if _UDIFF_NAME.match(name):
            return name_info(name)[0]
        raise UnsupportedFormatError("%s: file name is not cmDDMMMYYYYbhav.csv[.zip] or "
                                     "BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv[.zip]" % name)
    if m.group(2) not in _MONTHS:
        raise UnsupportedFormatError("%s: unknown month in file name" % name)
    try:
        return datetime.date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    except ValueError:
        raise UnsupportedFormatError("%s: file name date is not a real date" % name)


def _decimal(text, what):
    if not _DECIMAL.match(text):
        raise RowValueError("%s: %r is not a plain non-negative decimal" % (what, text))
    return Decimal(text)


def _whole(text, what):
    if not _WHOLE.match(text):
        raise RowValueError("%s: %r is not a whole number" % (what, text))
    return int(text)


def _row(fields, line, file_date, name):
    where = "%s line %d" % (name, line)
    if len(fields) != len(LEGACY_HEADER):
        raise MalformedFileError("%s: %d fields, expected %d" % (where, len(fields), len(LEGACY_HEADER)))
    if fields[13] != "":
        raise MalformedFileError("%s: the unnamed 14th column must be empty" % where)
    symbol, series = fields[0], fields[1]
    for label, value in (("SYMBOL", symbol), ("SERIES", series)):
        if not value or value != value.strip() or " " in value:
            raise MalformedFileError("%s: %s %r is empty or has spaces" % (where, label, value))
    trade_date = _date(fields[10], "%s TIMESTAMP" % where)      # structural: checked before any value
    if trade_date != file_date:
        raise MalformedFileError("%s: TIMESTAMP %s differs from the file name date %s"
                                 % (where, trade_date, file_date))
    o, h, l, c, last, prev = (_decimal(fields[i], "%s %s" % (where, LEGACY_HEADER[i])) for i in range(2, 8))
    if min(o, h, l, c) <= 0:
        raise RowValueError("%s: OPEN, HIGH, LOW and CLOSE must be above zero" % where)
    if not l <= min(o, c) <= max(o, c) <= h:
        raise RowValueError("%s: OHLC inconsistent (O %s H %s L %s C %s)" % (where, o, h, l, c))
    if not _ISIN.match(fields[12]):
        raise RowValueError("%s: ISIN %r is not IN + 10 letters or digits" % (where, fields[12]))
    return BhavRow(symbol, series, trade_date, o, h, l, c, last, prev,
                   _whole(fields[8], "%s TOTTRDQTY" % where),
                   _decimal(fields[9], "%s TOTTRDVAL" % where),
                   _whole(fields[11], "%s TOTALTRADES" % where),
                   fields[12], line)


def _udiff_row(fields, line, file_date, name):
    where = "%s line %d" % (name, line)
    if len(fields) != len(UDIFF_COLUMNS):
        raise MalformedFileError("%s: %d fields, expected %d" % (where, len(fields), len(UDIFF_COLUMNS)))
    f = dict(zip(UDIFF_COLUMNS, fields))
    if not _ISO_DATE.match(f["TradDt"]):
        raise MalformedFileError("%s: TradDt %r is not YYYY-MM-DD" % (where, f["TradDt"]))
    try:
        trade_date = datetime.date.fromisoformat(f["TradDt"])
    except ValueError:
        raise MalformedFileError("%s: TradDt %r is not a real date" % (where, f["TradDt"]))
    if trade_date != file_date:
        raise MalformedFileError("%s: TradDt %s differs from the file name date %s" % (where, trade_date, file_date))
    if f["BizDt"] != f["TradDt"]:
        raise UnsupportedFormatError("%s: BizDt %r differs from TradDt; not seen in the verified samples"
                                     % (where, f["BizDt"]))
    for col, want in _UDIFF_FIXED.items():
        if f[col] != want:
            raise UnsupportedFormatError("%s: %s %r; the verified samples have only %r" % (where, col, f[col], want))
    for col in _UDIFF_EMPTY:
        if f[col] != "":
            raise UnsupportedFormatError("%s: %s %r must be empty in a cash-market file" % (where, col, f[col]))
    symbol, series = f["TckrSymb"], f["SctySrs"]
    for label, value in (("TckrSymb", symbol), ("SctySrs", series)):
        if not value or value != value.strip() or " " in value:
            raise MalformedFileError("%s: %s %r is empty or has spaces" % (where, label, value))
    o, h, l, c, prev = (_decimal(f[k], "%s %s" % (where, k))
                        for k in ("OpnPric", "HghPric", "LwPric", "ClsPric", "PrvsClsgPric"))
    last = _decimal(f["LastPric"], "%s LastPric" % where) if f["LastPric"] != "" else None
    if min(o, h, l, c) <= 0:
        raise RowValueError("%s: OpnPric, HghPric, LwPric and ClsPric must be above zero" % where)
    if not l <= min(o, c) <= max(o, c) <= h:
        raise RowValueError("%s: OHLC inconsistent (O %s H %s L %s C %s)" % (where, o, h, l, c))
    if not _ISIN.match(f["ISIN"]):
        raise RowValueError("%s: ISIN %r is not IN + 10 letters or digits" % (where, f["ISIN"]))
    _whole(f["FinInstrmId"], "%s FinInstrmId" % where)
    _whole(f["NewBrdLotQty"], "%s NewBrdLotQty" % where)
    _decimal(f["SttlmPric"], "%s SttlmPric" % where)
    return BhavRow(symbol, series, trade_date, o, h, l, c, last, prev,
                   _whole(f["TtlTradgVol"], "%s TtlTradgVol" % where),
                   _decimal(f["TtlTrfVal"], "%s TtlTrfVal" % where),
                   _whole(f["TtlNbOfTxsExctd"], "%s TtlNbOfTxsExctd" % where),
                   f["ISIN"], line, tuple((k, f[k]) for k in UDIFF_EXTRA))


def _text(data, name, allow_crlf=False):
    """The CSV text after the encoding checks shared by both formats. With allow_crlf, a file
    whose every line ends in CRLF (and has no other CR) is returned with LF endings."""
    if not data:
        raise MalformedFileError("%s: empty file" % name)
    if data.startswith(b"\xef\xbb\xbf"):
        raise UnsupportedFormatError("%s: has a byte-order mark; the verified format has none" % name)
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise UnsupportedFormatError("%s: not ASCII; the verified format is ASCII only" % name)
    if "\r" in text:
        if not (allow_crlf and text.count("\r") == text.count("\r\n") == text.count("\n")):
            raise UnsupportedFormatError("%s: CR line endings; the verified format uses LF only" % name)
        text = text.replace("\r\n", "\n")
    if '"' in text:
        raise UnsupportedFormatError("%s: quote characters; the verified format has none" % name)
    if not text.endswith("\n"):
        raise MalformedFileError("%s: no final newline (truncated?)" % name)
    return text


def _parse(data, file_date, name, fmt=FORMAT_LEGACY):
    """(rows, schema_version). Each format accepts only its own verified headers."""
    crlf = fmt == FORMAT_LEGACY and b"\r" in data
    lines = _text(data, name, allow_crlf=crlf)[:-1].split("\n")
    header = tuple(lines[0].split(","))
    if fmt == FORMAT_UDIFF:
        schema = [k for k, v in UDIFF_SCHEMAS.items() if v == header]
        if not schema:
            raise UnsupportedFormatError("%s: header %r is not a verified UDiFF header (%s)"
                                         % (name, lines[0], ", ".join(sorted(UDIFF_SCHEMAS))))
        schema, parse_row = schema[0], _udiff_row
    else:
        if crlf:
            if header != LEGACY_HEADER_13:
                raise UnsupportedFormatError("%s: CRLF file whose header %r is not the verified 13-column header"
                                             % (name, lines[0]))
            schema = LEGACY_CRLF_SCHEMA
            short = _short_date(file_date)
            if len(lines) > 1 and lines[1].split(",")[10:11] == [short]:
                # cm13JUL2020bhav.csv (ED-38): every TIMESTAMP is the file date as DD-Mon-YY.
                # Only that exact string is accepted, on every row; it is rewritten to the
                # canonical form before the ordinary row checks.
                schema = LEGACY_CRLF_SHORTDATE_SCHEMA

                def parse_row(f, line, d, n):
                    if len(f) > 10:
                        if f[10] != short:
                            raise MalformedFileError("%s line %d TIMESTAMP: %r, expected %r on every row"
                                                     % (n, line, f[10], short))
                        f = f[:10] + [d.strftime("%d-") + _MONTH_NAMES[d.month] + d.strftime("-%Y")] + f[11:]
                    return _row(f + [""] if len(f) == 13 else f + ["?"], line, d, n)
            else:
                parse_row = lambda f, line, d, n: _row(f + [""] if len(f) == 13 else f + ["?"], line, d, n)
        elif header != LEGACY_HEADER:
            raise UnsupportedFormatError("%s: header %r is not the verified legacy header" % (name, lines[0]))
        else:
            schema, parse_row = LEGACY_SCHEMA, _row
    if len(lines) < 2:
        raise MalformedFileError("%s: no data rows" % name)
    rows, seen, rejected = [], {}, []
    series_at = UDIFF_COLUMNS.index("SctySrs") if fmt == FORMAT_UDIFF else 1
    symbol_at = UDIFF_COLUMNS.index("TckrSymb") if fmt == FORMAT_UDIFF else 0
    width = len(UDIFF_COLUMNS) if fmt == FORMAT_UDIFF else len(LEGACY_HEADER)
    for line, text_row in enumerate(lines[1:], start=2):
        fields = text_row.split(",")
        try:
            r = parse_row(fields, line, file_date, name)
        except RowValueError as e:
            # isolate only a value failure on a row whose structure is intact and whose series
            # is an uppercase non-EQ code (ED-30, QA 2026-11-09); everything else refuses the file
            series = fields[series_at] if len(fields) == width else ""
            if not _SERIES.match(series) or series == "EQ":
                raise
            rejected.append((line, series, fields[symbol_at], str(e)))      # isolated (ED-30)
            continue
        key = (r.symbol, r.series)
        if key in seen:
            raise MalformedFileError("%s: duplicate %s %s on %s (lines %d and %d)"
                                     % (name, r.symbol, r.series, r.trade_date, seen[key], line))
        seen[key] = line
        rows.append(r)
    return rows, schema, tuple(rejected)


def read_manifest(path):
    """Rows of a manifest whose header is exactly MANIFEST_COLUMNS."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != MANIFEST_COLUMNS:
            raise ProvenanceError("%s: header must be exactly %s"
                                  % (os.path.basename(path), ",".join(MANIFEST_COLUMNS)))
        return [dict(r) for r in reader]


def _match(records, kind, name, size, sha, trade_date, parent=None):
    """The one record of this kind and name (and parent archive, when given)."""
    found = [r for r in records if r["kind"] == kind and r["file_name"] == name
             and (parent is None or r["parent_archive"] == parent)]
    if len(found) != 1:
        raise ProvenanceError("%s: %d %s manifest records (need exactly 1)" % (name, len(found), kind))
    r = found[0]
    if r["size_bytes"] != str(size) or r["sha256"] != sha:
        raise ProvenanceError("%s: size or SHA-256 differs from the manifest" % name)
    if r["trade_date"] != trade_date.isoformat():
        raise ProvenanceError("%s: manifest trade_date %s differs from the file name date" % (name, r["trade_date"]))
    return r


def archive_layout_ok(name, members):
    """True when the archive holds exactly one member with the official name. One recorded
    variant is also accepted: the member stored under a folder of its own name
    ("cmDDMMMYYYYbhav.csv/cmDDMMMYYYYbhav.csv"), as NSE serves cm13JUL2020bhav.csv.zip
    (ED-38). Any other layout is refused."""
    member = name[:-len(".zip")]
    return len(members) == 1 and members[0] in (member, member + "/" + member)


def load(path, manifest=None):
    """Load one bhavcopy, legacy or UDiFF (archive or CSV). manifest: path to manifest.csv, or
    rows from read_manifest(); when given, the file must match it."""
    name = os.path.basename(path)
    file_date, fmt = name_info(name)
    with open(path, "rb") as fh:
        data = fh.read()
    if name.endswith(".zip"):
        member = name[:-len(".zip")]
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                infos = z.infolist()
                if not archive_layout_ok(name, [i.filename for i in infos]):
                    raise UnsupportedFormatError("%s: must hold exactly one member named %s, found %s"
                                                 % (name, member, [i.filename for i in infos]))
                if infos[0].file_size > MAX_MEMBER_BYTES:
                    raise UnsupportedFormatError("%s: member larger than %d bytes" % (name, MAX_MEMBER_BYTES))
                csv_bytes = z.read(infos[0])
        except zipfile.BadZipFile as e:
            raise MalformedFileError("%s: not a readable zip archive (%s)" % (name, e))
        source = SourceInfo(name, "ARCHIVE", len(data), _sha256(data), infos[0].filename, len(csv_bytes),
                            _sha256(csv_bytes))
    else:
        csv_bytes = data
        source = SourceInfo(name, "CSV", len(data), _sha256(data), None, None, None)

    provenance = None
    if manifest is not None:
        records = read_manifest(manifest) if isinstance(manifest, str) else manifest
        if source.kind == "ARCHIVE":
            provenance = _match(records, "ARCHIVE", name, source.size_bytes, source.sha256, file_date)
            _match(records, "ARCHIVE_MEMBER", source.member_name, source.member_size_bytes,
                   source.member_sha256, file_date, parent=name)
        else:
            provenance = _match(records, "STANDALONE_COPY", name, source.size_bytes, source.sha256, file_date)

    rows, schema, rejected = _parse(csv_bytes, file_date, name, fmt)
    counts = {}
    for r in rows:
        counts[r.series] = counts.get(r.series, 0) + 1
    with_eq = set(r.symbol for r in rows if r.series == "EQ")
    non_eq_only = sorted(set(r.symbol for r in rows) - with_eq)
    return BhavcopyFile(source=source, trade_date=file_date, rows=rows, series_counts=counts,
                        non_eq_only_symbols=non_eq_only, provenance=provenance, format=fmt,
                        schema_version=schema, rejected_rows=rejected)


def load_many(paths, manifest=None, keep=None):
    """Load several files, oldest first. Two files for one trade date (e.g. an archive
    and its own CSV copy, or a legacy and a UDiFF file) are refused: one date's records
    must come from one file. A file not in the format selected for its date is refused
    (SourceSelectionError, ED-20), so a dataset never mixes the two sources for a date.

    keep: optional predicate on a BhavRow. Every row of every file is still parsed and
    validated in full, and series_counts / non_eq_only_symbols still describe the whole
    file; only the rows kept stay in memory (ten years of rows do not fit in 8 GB, ED-41)."""
    records = read_manifest(manifest) if isinstance(manifest, str) else manifest
    files = []
    for p in paths:
        f = load(p, records)
        if keep is not None:
            f = replace(f, rows=[r for r in f.rows if keep(r)])
        files.append(f)
    by_date = {}
    for f in files:
        if f.format != selected_format(f.trade_date):
            raise SourceSelectionError("%s: %s for %s, but %s is the selected source for that date (ED-20)"
                                       % (f.source.file_name, f.format, f.trade_date, selected_format(f.trade_date)))
        if f.trade_date in by_date:
            raise BhavcopyError("two files for trade date %s: %s and %s"
                                % (f.trade_date, by_date[f.trade_date].source.file_name, f.source.file_name))
        by_date[f.trade_date] = f
    return [by_date[d] for d in sorted(by_date)]


CROSS_CHECK_FIELDS = ("isin", "open", "high", "low", "close", "last", "prev_close", "traded_qty",
                      "traded_value", "total_trades")


def cross_check(a, b):
    """Compare two loaded files for one trade date (typically legacy and UDiFF on an overlap
    date), row by (symbol, series), field by field, exactly (tolerance 0; Decimal equality,
    so 3197 equals 3197.00). The one known representational difference is counted, not
    hidden: an empty UDiFF LastPric against a legacy LAST of 0 (LAST_EMPTY_VS_ZERO).
    Returns a dict; "identical" is True only with no missing key and no mismatch."""
    if a.trade_date != b.trade_date:
        raise BhavcopyError("cross_check needs one trade date: %s and %s" % (a.trade_date, b.trade_date))
    ka = {(r.symbol, r.series): r for r in a.rows}
    kb = {(r.symbol, r.series): r for r in b.rows}
    mismatches, last_empty_vs_zero = [], 0
    for key in sorted(set(ka) & set(kb)):
        ra, rb = ka[key], kb[key]
        for field_name in CROSS_CHECK_FIELDS:
            va, vb = getattr(ra, field_name), getattr(rb, field_name)
            if va == vb:
                continue
            if field_name == "last" and {va, vb} == {None, Decimal(0)}:
                last_empty_vs_zero += 1
                continue
            mismatches.append({"symbol": key[0], "series": key[1], "field": field_name,
                               a.format: str(va), b.format: str(vb)})
    only_a, only_b = sorted(set(ka) - set(kb)), sorted(set(kb) - set(ka))
    return {"trade_date": a.trade_date.isoformat(), "files": [a.source.file_name, b.source.file_name],
            "rows": [len(ka), len(kb)], "common_rows": len(set(ka) & set(kb)),
            "only_in_first": [list(k) for k in only_a], "only_in_second": [list(k) for k in only_b],
            "mismatches": mismatches, "last_empty_vs_zero": last_empty_vs_zero,
            "identical": not (mismatches or only_a or only_b)}
