"""Manifest rows for newly downloaded legacy bhavcopy archives (D31: the user downloads;
nothing is fetched here).

For each cmDDMMMYYYYbhav.csv.zip it computes, from the bytes on disk, the ARCHIVE row and
the ARCHIVE_MEMBER row that nse_bhavcopy.load_many(paths, manifest) requires (size and
SHA-256 of both), after the strict loader has parsed the file. What only the user knows is
passed in and never inferred: the source page, the download date (YYYY-MM-DD or UNKNOWN;
never a file's modification time) and the provenance status. A file already in the
manifest, a date held twice, or a file the strict loader refuses is an error.
"""

import csv
import datetime
import io
import os

from nse.research.deps import bhavcopy

DOWNLOAD_DATE_UNKNOWN = "UNKNOWN"


class ManifestError(ValueError):
    pass


def rows_for(paths, manifest_path, source_page, downloaded_on, provenance_status):
    if not source_page.strip():
        raise ManifestError("source_page is required (the page the files were downloaded from)")
    if downloaded_on != DOWNLOAD_DATE_UNKNOWN:
        try:
            datetime.date.fromisoformat(downloaded_on)
        except ValueError:
            raise ManifestError("downloaded_on must be YYYY-MM-DD or UNKNOWN")
    if not provenance_status.strip() or "," in provenance_status:
        raise ManifestError("provenance_status is required and may not contain a comma")
    existing = bhavcopy.read_manifest(manifest_path)
    held_names = set(r["file_name"] for r in existing)
    held_dates = set(r["trade_date"] for r in existing if r["kind"] == "ARCHIVE")
    out, seen = [], set()
    for p in sorted(paths):
        name = os.path.basename(p)
        if not name.endswith(".csv.zip"):
            raise ManifestError("%s: only legacy cmDDMMMYYYYbhav.csv.zip archives are supported (UDiFF: B18)" % name)
        f = bhavcopy.load(p)                      # strict parse; raises on any deviation
        d = f.trade_date.isoformat()
        if name in held_names or f.source.member_name in held_names:
            raise ManifestError("%s: already in the manifest" % name)
        if d in held_dates or d in seen:
            raise ManifestError("%s: trade date %s is already held" % (name, d))
        seen.add(d)
        s = f.source
        out.append({"file_name": name, "kind": "ARCHIVE", "parent_archive": "", "trade_date": d,
                    "size_bytes": str(s.size_bytes), "sha256": s.sha256, "source_page": source_page,
                    "downloaded_on": downloaded_on, "provenance_status": provenance_status})
        out.append({"file_name": s.member_name, "kind": "ARCHIVE_MEMBER", "parent_archive": name, "trade_date": d,
                    "size_bytes": str(s.member_size_bytes), "sha256": s.member_sha256, "source_page": source_page,
                    "downloaded_on": downloaded_on, "provenance_status": provenance_status + "_VIA_ARCHIVE"})
    return out


def to_csv(rows, header=False):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(bhavcopy.MANIFEST_COLUMNS), lineterminator="\n")
    if header:
        w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def append(manifest_path, rows):
    with open(manifest_path, "rb") as fh:
        data = fh.read()
    with open(manifest_path, "a", encoding="utf-8", newline="") as fh:
        if data and not data.endswith(b"\n"):
            fh.write("\n")
        fh.write(to_csv(rows))
