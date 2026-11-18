"""Log lines never keep a session cookie value."""

from __future__ import annotations

import logging
import re

_COOKIE = re.compile(r"(gtf_session=)[^;\s]+", re.I)


def redact(text: str) -> str:
    return _COOKIE.sub(r"\1[redacted]", text)


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            if record.args:
                record.msg = redact(record.getMessage())
                record.args = ()
            else:
                record.msg = redact(record.msg)
        return True


def install() -> None:
    logger = logging.getLogger("gtf_platform")
    if not any(isinstance(item, RedactFilter) for item in logger.filters):
        logger.addFilter(RedactFilter())
    logger.setLevel(logging.INFO)
