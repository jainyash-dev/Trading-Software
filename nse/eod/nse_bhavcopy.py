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
  - Prices are kept exactly as published, as Decimal: unadjusted for corporate actions
    (B7). Nothing here adjusts them.
  - Rows of every series are kept. eq_rows gives the EQ rows (DATA_REQUIREMENTS §2.2);
    non_eq_series counts the others, and non_eq_only_symbols lists symbols that have
    rows on the day but no EQ row (EOD_FORMAT_EVIDENCE §7.3), so an EQ filter can never
    hide them silently.
  - UDiFF is not supported. A UDiFF file is refused as an unsupported format; nothing
    switches format by date (the switch date is unverified).
  - The output is data only: no candles, session times, zones or eligibility. Turning a
    trade date into a candle is a separate step (audit L7: the 15:30 close is assumed).

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
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

LOADER_VERSION = "1.0.0"
FORMAT = "NSE_CM_BHAVCOPY_LEGACY"
PRICE_ADJUSTMENT = "NONE"           # as published, unadjusted (B7)

# EOD_FORMAT_EVIDENCE.md section 5; the empty last name is the trailing comma's column
LEGACY_HEADER = ("SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE",
                 "TOTTRDQTY", "TOTTRDVAL", "TIMESTAMP", "TOTALTRADES", "ISIN", "")
MANIFEST_COLUMNS = ("file_name", "kind", "parent_archive", "trade_date", "size_bytes",
                    "sha256", "source_page", "downloaded_on", "provenance_status")
MAX_MEMBER_BYTES = 50 * 1024 * 1024  # the verified members are about 0.25 MB

_NAME = re.compile(r"cm(\d{2})([A-Z]{3})(\d{4})bhav\.csv(\.zip)?\Z")
_DATE = re.compile(r"(\d{2})-([A-Z]{3})-(\d{4})\Z")
_DECIMAL = re.compile(r"\d+(\.\d+)?\Z")
_WHOLE = re.compile(r"\d+\Z")
_ISIN = re.compile(r"IN[A-Z0-9]{10}\Z")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"))}


class BhavcopyError(ValueError):
    """The file is refused; nothing from it is used."""


class UnsupportedFormatError(BhavcopyError):
    """Not the verified legacy format (name, archive layout, encoding or header)."""


class MalformedFileError(BhavcopyError):
    """The legacy format, but the file or a row is invalid."""


class ProvenanceError(BhavcopyError):
    """The file does not match its manifest record."""


@dataclass(frozen=True)
class BhavRow:
    symbol: str
    series: str
    trade_date: datetime.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    last: Decimal
    prev_close: Decimal
    traded_qty: int
    traded_value: Decimal
    total_trades: int
    isin: str
    line: int                       # line number in the CSV (header = 1)


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
    rows: List[BhavRow]             # every row, every series, in file order
    series_counts: Dict[str, int]
    non_eq_only_symbols: List[str]  # rows on the day, but no EQ row
    provenance: Optional[Dict[str, str]]   # the manifest record, verbatim
    format: str = FORMAT
    loader_version: str = LOADER_VERSION
    price_adjustment: str = PRICE_ADJUSTMENT

    @property
    def eq_rows(self):
        return [r for r in self.rows if r.series == "EQ"]

    @property
    def non_eq_series(self):
        return {s: n for s, n in self.series_counts.items() if s != "EQ"}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _date(text, what):
    m = _DATE.match(text)
    if not m or m.group(2) not in _MONTHS:
        raise MalformedFileError("%s: %r is not DD-MMM-YYYY" % (what, text))
    try:
        return datetime.date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    except ValueError:
        raise MalformedFileError("%s: %r is not a real date" % (what, text))


def _name_date(name):
    m = _NAME.match(name)
    if not m:
        raise UnsupportedFormatError("%s: file name is not cmDDMMMYYYYbhav.csv[.zip]" % name)
    if m.group(2) not in _MONTHS:
        raise UnsupportedFormatError("%s: unknown month in file name" % name)
    try:
        return datetime.date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    except ValueError:
        raise UnsupportedFormatError("%s: file name date is not a real date" % name)


def _decimal(text, what):
    if not _DECIMAL.match(text):
        raise MalformedFileError("%s: %r is not a plain non-negative decimal" % (what, text))
    return Decimal(text)


def _whole(text, what):
    if not _WHOLE.match(text):
        raise MalformedFileError("%s: %r is not a whole number" % (what, text))
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
    o, h, l, c, last, prev = (_decimal(fields[i], "%s %s" % (where, LEGACY_HEADER[i])) for i in range(2, 8))
    if min(o, h, l, c) <= 0:
        raise MalformedFileError("%s: OPEN, HIGH, LOW and CLOSE must be above zero" % where)
    if not l <= min(o, c) <= max(o, c) <= h:
        raise MalformedFileError("%s: OHLC inconsistent (O %s H %s L %s C %s)" % (where, o, h, l, c))
    trade_date = _date(fields[10], "%s TIMESTAMP" % where)
    if trade_date != file_date:
        raise MalformedFileError("%s: TIMESTAMP %s differs from the file name date %s"
                                 % (where, trade_date, file_date))
    if not _ISIN.match(fields[12]):
        raise MalformedFileError("%s: ISIN %r is not IN + 10 letters or digits" % (where, fields[12]))
    return BhavRow(symbol, series, trade_date, o, h, l, c, last, prev,
                   _whole(fields[8], "%s TOTTRDQTY" % where),
                   _decimal(fields[9], "%s TOTTRDVAL" % where),
                   _whole(fields[11], "%s TOTALTRADES" % where),
                   fields[12], line)


def _parse(data, file_date, name):
    if not data:
        raise MalformedFileError("%s: empty file" % name)
    if data.startswith(b"\xef\xbb\xbf"):
        raise UnsupportedFormatError("%s: has a byte-order mark; the verified format has none" % name)
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise UnsupportedFormatError("%s: not ASCII; the verified format is ASCII only" % name)
    if "\r" in text:
        raise UnsupportedFormatError("%s: CR line endings; the verified format uses LF only" % name)
    if '"' in text:
        raise UnsupportedFormatError("%s: quote characters; the verified format has none" % name)
    if not text.endswith("\n"):
        raise MalformedFileError("%s: no final newline (truncated?)" % name)
    lines = text[:-1].split("\n")
    header = tuple(lines[0].split(","))
    if header != LEGACY_HEADER:
        raise UnsupportedFormatError("%s: header %r is not the verified legacy header" % (name, lines[0]))
    if len(lines) < 2:
        raise MalformedFileError("%s: no data rows" % name)
    rows, seen = [], {}
    for line, text_row in enumerate(lines[1:], start=2):
        r = _row(text_row.split(","), line, file_date, name)
        key = (r.symbol, r.series)
        if key in seen:
            raise MalformedFileError("%s: duplicate %s %s on %s (lines %d and %d)"
                                     % (name, r.symbol, r.series, r.trade_date, seen[key], line))
        seen[key] = line
        rows.append(r)
    return rows


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


def load(path, manifest=None):
    """Load one legacy bhavcopy (archive or CSV). manifest: path to manifest.csv, or
    rows from read_manifest(); when given, the file must match it."""
    name = os.path.basename(path)
    file_date = _name_date(name)
    with open(path, "rb") as fh:
        data = fh.read()
    if name.endswith(".zip"):
        member = name[:-len(".zip")]
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                infos = z.infolist()
                if len(infos) != 1 or infos[0].filename != member:
                    raise UnsupportedFormatError("%s: must hold exactly one member named %s, found %s"
                                                 % (name, member, [i.filename for i in infos]))
                if infos[0].file_size > MAX_MEMBER_BYTES:
                    raise UnsupportedFormatError("%s: member larger than %d bytes" % (name, MAX_MEMBER_BYTES))
                csv_bytes = z.read(infos[0])
        except zipfile.BadZipFile as e:
            raise MalformedFileError("%s: not a readable zip archive (%s)" % (name, e))
        source = SourceInfo(name, "ARCHIVE", len(data), _sha256(data), member, len(csv_bytes), _sha256(csv_bytes))
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

    rows = _parse(csv_bytes, file_date, name)
    counts = {}
    for r in rows:
        counts[r.series] = counts.get(r.series, 0) + 1
    with_eq = set(r.symbol for r in rows if r.series == "EQ")
    non_eq_only = sorted(set(r.symbol for r in rows) - with_eq)
    return BhavcopyFile(source=source, trade_date=file_date, rows=rows, series_counts=counts,
                        non_eq_only_symbols=non_eq_only, provenance=provenance)


def load_many(paths, manifest=None):
    """Load several files, oldest first. Two files for one trade date (e.g. an archive
    and its own CSV copy) are refused: one date's records must come from one file."""
    records = read_manifest(manifest) if isinstance(manifest, str) else manifest
    files = [load(p, records) for p in paths]
    by_date = {}
    for f in files:
        if f.trade_date in by_date:
            raise BhavcopyError("two files for trade date %s: %s and %s"
                                % (f.trade_date, by_date[f.trade_date].source.file_name, f.source.file_name))
        by_date[f.trade_date] = f
    return [by_date[d] for d in sorted(by_date)]
