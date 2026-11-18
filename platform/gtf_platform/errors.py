"""Structured API errors. Messages are fixed strings and never include cookies."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = dict(details or {})


def error_body(exc: ApiError) -> dict:
    return {"error": {"code": exc.code, "message": exc.message, "details": exc.details}}


def reject_mixed_fixture(body: object) -> None:
    """A fixture payload must not cite a real dataset id (API contract)."""
    if not isinstance(body, dict):
        return
    meta = body.get("meta")
    data = body.get("data")
    fixture = isinstance(meta, dict) and meta.get("fixture") is True
    dataset = data.get("dataset_id") if isinstance(data, dict) else None
    if fixture and dataset not in (None, ""):
        raise ApiError(
            422,
            "REQUEST_INVALID",
            "A fixture payload cannot cite a real dataset id",
        )
