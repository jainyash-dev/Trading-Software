"""Itemised cash-equity charge arithmetic for the research journal.

No brokerage, STT, exchange, SEBI, GST or stamp rate is stored in this module.
A result exists only when the caller supplies a dated schedule or an owner-entered
amount. A missing schedule is an error here, and the journal records nothing, which
the summary reports as ABSENT. Slippage is not a charge.
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP

COMPONENTS = ("BROKERAGE", "STT", "EXCHANGE", "SEBI", "GST", "STAMP", "OTHER")
_PAISE = Decimal("1")
_HUNDRED = Decimal("100")
_TEN_THOUSAND = Decimal("10000")


class ChargeScheduleError(ValueError):
    """The schedule is missing, undated, or does not cover this fill."""


def quote(schedule, *, side, quantity, price, trade_date):
    """Itemise one fill. ``schedule`` is the owner's dated document, not a built-in tariff.

    ``side`` is BUY or SELL. ``quantity`` is a positive share count. ``price`` is the
    execution price. ``trade_date`` must fall inside the schedule's inclusive dates.
    Money is rounded half-up to paise, once per component, after that component's own basis.
    GST is a percent of named components already computed for this side. It is not
    applied to itself and it is not added into those components.
    """
    if not isinstance(schedule, dict):
        raise ChargeScheduleError("a charge schedule is required; nothing is assumed")
    if side not in ("BUY", "SELL"):
        raise ChargeScheduleError("side must be BUY or SELL")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ChargeScheduleError("quantity must be a positive whole number of shares")
    px = _decimal(price, "price")
    if px <= 0:
        raise ChargeScheduleError("price must be positive")
    day = _date(trade_date)
    start = _date(schedule.get("effective_from"), "effective_from")
    end = _date(schedule.get("effective_to"), "effective_to")
    if end < start:
        raise ChargeScheduleError("schedule ends before it starts")
    if day < start or day > end:
        raise ChargeScheduleError("no schedule covers %s (%s to %s)" % (day, start, end))
    source = schedule.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ChargeScheduleError("schedule source is required")
    raw = schedule.get("components")
    if not isinstance(raw, list) or not raw:
        raise ChargeScheduleError("schedule components must be a non-empty list")
    present = []
    ordinary = []
    percent_of = []
    for row in raw:
        if not isinstance(row, dict):
            raise ChargeScheduleError("each component must be an object")
        code = row.get("code")
        if code not in COMPONENTS:
            raise ChargeScheduleError("unknown component %r" % (code,))
        if code in present:
            raise ChargeScheduleError("component %s is repeated" % code)
        present.append(code)
        if row.get("model") == "PERCENT_OF_COMPONENTS":
            percent_of.append(row)
        else:
            ordinary.append(row)
    lines = []
    amounts = {}
    for row in ordinary:
        amount, basis = _ordinary(row, side, quantity, px)
        amounts[row["code"]] = amount
        lines.append({"component": row["code"], "amount_paise": amount, "basis": basis})
    for row in percent_of:
        amount, basis = _percent(row, side, amounts)
        amounts[row["code"]] = amount
        lines.append({"component": row["code"], "amount_paise": amount, "basis": basis})
    coverage = "COMPLETE" if set(COMPONENTS) <= set(present) else "PARTIAL"
    return {
        "state": "ESTIMATED",
        "coverage": coverage,
        "side": side,
        "quantity": quantity,
        "price": format(px, "f"),
        "trade_date": day.isoformat(),
        "source": source.strip(),
        "effective_from": start.isoformat(),
        "effective_to": end.isoformat(),
        "lines": lines,
        "total_paise": sum(line["amount_paise"] for line in lines),
        "note": "Estimated from the supplied schedule. Not an official tariff and not a broker pull.",
    }


def _ordinary(row, side, quantity, price):
    spec = row.get(side)
    if not isinstance(spec, dict):
        raise ChargeScheduleError("%s needs a %s rule" % (row.get("code"), side))
    model = spec.get("model")
    code = row["code"]
    if model == "NONE":
        return 0, "%s not charged on %s" % (code, side)
    if model == "FLAT_RUPEES":
        rupees = _decimal(spec.get("rupees"), "%s rupees" % code)
        if rupees < 0:
            raise ChargeScheduleError("%s rupees must be >= 0" % code)
        return _paise(rupees), "%s flat %s rupees on %s" % (code, format(rupees, "f"), side)
    if model == "BPS_OF_VALUE":
        bps = _decimal(spec.get("bps"), "%s bps" % code)
        if bps < 0:
            raise ChargeScheduleError("%s bps must be >= 0" % code)
        rupees = (Decimal(quantity) * price * bps) / _TEN_THOUSAND
        return _paise(rupees), "%s %s bps of quantity x price on %s" % (code, format(bps, "f"), side)
    raise ChargeScheduleError("%s model %r is not NONE, FLAT_RUPEES or BPS_OF_VALUE" % (code, model))


def _percent(row, side, amounts):
    code = row["code"]
    percent = _decimal(row.get("percent"), "%s percent" % code)
    if percent < 0:
        raise ChargeScheduleError("%s percent must be >= 0" % code)
    names = row.get("of")
    if not isinstance(names, list) or not names:
        raise ChargeScheduleError("%s must name the components it is charged on" % code)
    if code in names:
        raise ChargeScheduleError("%s cannot include itself" % code)
    missing = [name for name in names if name not in amounts]
    if missing:
        raise ChargeScheduleError("%s refers to %s before those components are computed" % (code, ", ".join(missing)))
    rupees = (sum((Decimal(amounts[name]) for name in names), Decimal(0)) / _HUNDRED) * percent / _HUNDRED
    basis = "%s %s percent of %s on %s" % (code, format(percent, "f"), "+".join(names), side)
    return _paise(rupees), basis


def _paise(rupees):
    return int((rupees * _HUNDRED).quantize(_PAISE, rounding=ROUND_HALF_UP))


def _decimal(value, what):
    if isinstance(value, bool) or value is None:
        raise ChargeScheduleError("%s is required" % what)
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise ChargeScheduleError("%s is not a number" % what) from exc
    if not number.is_finite():
        raise ChargeScheduleError("%s is not finite" % what)
    return number


def _date(value, what="trade_date"):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError as exc:
            raise ChargeScheduleError("%s is not a date" % what) from exc
    raise ChargeScheduleError("%s is not a date" % what)
