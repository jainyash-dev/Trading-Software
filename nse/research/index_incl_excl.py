"""Read NSE's IndexInclExcl.xls far enough to test whether it is a membership baseline.

The workbook is a BIFF8 compound document. This reader uses the standard library.
It extracts sheet names and the Nifty 100 sheet's four columns. It does not map a
company name to a symbol or an ISIN, and it does not emit universe rows.

What the held file is, once parsed: a change log of company names. It has no ISIN,
no ticker, no opening list of 100 members, and no Nifty 100 event on or after
2020-12-31. That is not a point-in-time baseline (D59, D49).
"""

import datetime
import hashlib
import struct

_HEADER = ("Index Name", "Event Date", "Scrip Name", "Description")
_EXCEL_EPOCH = datetime.date(1899, 12, 30)


class IndexInclExclError(ValueError):
    pass


def _rk(value):
    """Excel RK number (MS-XLS)."""
    if value & 2:
        number = struct.unpack("<i", struct.pack("<I", value & 0xFFFFFFFC))[0] >> 2
        number = float(number)
    else:
        number = struct.unpack("<d", struct.pack("<II", 0, value & 0xFFFFFFFC))[0]
    if value & 1:
        number /= 100.0
    return number


def _excel_date(number):
    if not 30000 <= number <= 60000:
        return None
    return _EXCEL_EPOCH + datetime.timedelta(days=int(number))


def _workbook(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise IndexInclExclError("%s: not an OLE compound document" % path)
    sector_size = 1 << struct.unpack_from("<H", data, 0x1E)[0]

    def sector(index):
        return 512 + index * sector_size

    difat = []
    for i in range(109):
        value = struct.unpack_from("<I", data, 0x4C + 4 * i)[0]
        if value == 0xFFFFFFFF:
            break
        difat.append(value)
    fat = b"".join(data[sector(s):sector(s) + sector_size] for s in difat)

    def fat_next(index):
        return struct.unpack_from("<I", fat, index * 4)[0]

    def chain(start):
        out, seen = [], set()
        index = start
        while index < 0xFFFFFFF0 and index not in seen:
            seen.add(index)
            out.append(index)
            index = fat_next(index)
        return b"".join(data[sector(s):sector(s) + sector_size] for s in out)

    directory = chain(struct.unpack_from("<I", data, 0x30)[0])
    for offset in range(0, len(directory), 128):
        entry = directory[offset:offset + 128]
        name_bytes = struct.unpack_from("<H", entry, 64)[0]
        name = entry[:name_bytes].decode("utf-16le", "ignore").rstrip("\x00")
        if name == "Workbook":
            start = struct.unpack_from("<I", entry, 116)[0]
            size = struct.unpack_from("<I", entry, 120)[0]
            return chain(start)[:size]
    raise IndexInclExclError("%s: no Workbook stream" % path)


def _records(workbook):
    out, pos = [], 0
    while pos + 4 <= len(workbook):
        opcode, length = struct.unpack_from("<HH", workbook, pos)
        out.append((opcode, workbook[pos + 4:pos + 4 + length]))
        pos += 4 + length
    return out


def _shared_strings(records):
    for index, (opcode, record) in enumerate(records):
        if opcode != 0x00FC:
            continue
        parts = [record]
        cursor = index + 1
        while cursor < len(records) and records[cursor][0] == 0x003C:
            parts.append(records[cursor][1])
            cursor += 1
        unique = struct.unpack_from("<I", parts[0], 4)[0]
        bodies = [parts[0][8:]] + parts[1:]
        body_index, at = 0, 0

        def take(count, inside=False):
            nonlocal body_index, at
            got = b""
            while len(got) < count:
                if body_index >= len(bodies):
                    raise IndexInclExclError("shared-string table ended early")
                if at >= len(bodies[body_index]):
                    body_index += 1
                    at = 1 if inside else 0
                    continue
                step = min(count - len(got), len(bodies[body_index]) - at)
                got += bodies[body_index][at:at + step]
                at += step
            return got

        strings = []
        for _ in range(unique):
            chars = struct.unpack("<H", take(2))[0]
            flags = take(1)[0]
            wide = bool(flags & 1)
            rich = struct.unpack("<H", take(2))[0] if flags & 8 else 0
            extra = struct.unpack("<I", take(4))[0] if flags & 4 else 0
            raw = take(chars * (2 if wide else 1), inside=True)
            text = raw.decode("utf-16le" if wide else "latin1", "replace")
            if flags & 8:
                take(4 * rich)
            if flags & 4:
                take(extra)
            strings.append(text)
        return strings
    return []


def _sheet_names(records):
    names = []
    for opcode, record in records:
        if opcode != 0x0085 or len(record) < 8:
            continue
        count = record[6]
        wide = record[7] & 1
        raw = record[8:8 + count * (2 if wide else 1)]
        names.append(raw.decode("utf-16le" if wide else "latin1", "replace"))
    return names


def _sheet_cells(records, strings, sheet_name):
    names = _sheet_names(records)
    if sheet_name not in names:
        raise IndexInclExclError("sheet %r is not in %s" % (sheet_name, names))
    target = names.index(sheet_name)
    seen_global = False
    sheet_index = -1
    active = False
    cells = {}
    for opcode, record in records:
        if opcode == 0x0809:
            if not seen_global:
                seen_global = True
            else:
                sheet_index += 1
                active = sheet_index == target
            continue
        if not active:
            continue
        if opcode == 0x00FD and len(record) >= 10:
            row, col, _xf, which = struct.unpack_from("<HHHI", record)
            cells[(row, col)] = strings[which]
        elif opcode == 0x027E and len(record) >= 10:
            row, col = struct.unpack_from("<HH", record)
            cells[(row, col)] = _rk(struct.unpack_from("<I", record, 6)[0])
        elif opcode == 0x0203 and len(record) >= 14:
            row, col = struct.unpack_from("<HH", record)
            cells[(row, col)] = struct.unpack_from("<d", record, 6)[0]
    return names, cells


def _event_date(value):
    if isinstance(value, str):
        text = value.strip()
        try:
            return datetime.datetime.strptime(text, "%d-%m-%Y").date()
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        return _excel_date(float(value))
    return None


def inspect(path, sheet="Nifty 100"):
    """Facts needed to decide whether this workbook can be a membership baseline.

    `baseline_established` is true only when the sheet has ISINs or tickers, an
    opening composition, and an event or snapshot on or after 2020-12-31. This
    file's shape fails those tests. The caller still has to read `reasons`.
    """
    workbook = _workbook(path)
    records = _records(workbook)
    strings = _shared_strings(records)
    names, cells = _sheet_cells(records, strings, sheet)
    header = tuple(cells.get((0, col), "") for col in range(4))
    rows = []
    dates = []
    isin_cells = 0
    for row in sorted({r for r, _c in cells if r}):
        values = [cells.get((row, col), "") for col in range(4)]
        if not any(values):
            continue
        when = _event_date(values[1])
        if when:
            dates.append(when)
        for value in values:
            if isinstance(value, str) and value.strip().upper().startswith("INE"):
                isin_cells += 1
        rows.append({"index_name": values[0], "event_date": None if when is None else when.isoformat(),
                     "scrip_name": values[2] if isinstance(values[2], str) else "",
                     "description": values[3] if isinstance(values[3], str) else ""})
    inclusions = sum(1 for r in rows if r["description"].strip() == "Inclusion into Index")
    exclusions = sum(1 for r in rows if r["description"].strip() == "Exclusion from Index")
    latest = max(dates) if dates else None
    reasons = []
    if header != _HEADER:
        reasons.append("header is %s, not %s" % (header, _HEADER))
    if isin_cells:
        reasons.append("%d ISIN cells were present; this reader does not promote them without a review" % isin_cells)
    else:
        reasons.append("the Nifty 100 sheet has no ISIN")
    if not any(isinstance(cells.get((r, 2)), str) and cells.get((r, 2), "").isupper() and " " not in cells.get((r, 2), "")
               for r, _c in cells):
        reasons.append("the scrip column holds company names, not NSE symbols")
    reasons.append("the sheet is an inclusion and exclusion log (%d in, %d out), not an opening list of 100 members"
                   % (inclusions, exclusions))
    if latest is None or latest < datetime.date(2020, 12, 31):
        reasons.append("latest Nifty 100 event date is %s, before the 2020-12-31 research baseline" % latest)
    else:
        reasons.append("an event on or after 2020-12-31 is present and still has no symbol or ISIN")
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return {
        "sha256": digest,
        "sheets": names,
        "header": list(header),
        "nifty100_rows": len(rows),
        "inclusions": inclusions,
        "exclusions": exclusions,
        "isin_cells": isin_cells,
        "earliest_event": None if not dates else min(dates).isoformat(),
        "latest_event": None if latest is None else latest.isoformat(),
        "baseline_established": False,
        "reasons": reasons,
        "rows": rows,
    }
