"""Overtime as a balance, summed one day at a time.

A workday contributes what was logged minus eight hours, so a short day pays off a long one:
eight hours of overtime taken back as a day off nets to zero. A weekend or a public holiday
contributes everything logged on it, because none of it was owed.

Two kinds of day owe nothing. Workdays before the first logged hour precede this Tempo, and
the last day of the range is still in progress — its surplus counts, its shortfall not yet.

Which days are workdays is never decided here. The skill already marks every day it returns
with `workday`, so the hub holds no calendar and knows no Polish holiday.

Nothing in this module filters by ticket. An hour booked on an absence or an administrative
key is an hour that was logged, and a rail that silently dropped some of them would be
answering a question nobody asked.
"""
import os

from . import store
from .tempo import TARGET_HOURS


def _empty():
    return {"total": 0.0, "months": [], "year": ""}


def _balance(day, owes):
    logged = day.get("total_hours") or 0

    if not day.get("workday"):
        return logged

    balance = logged - TARGET_HOURS

    return balance if owes else max(0.0, balance)


def by_month(days, until=None):
    """One entry per month that holds at least one logged hour, newest first.

    `until` is the last day of the range, the one still in progress.

    A month nothing was ever logged in is not a month of zero overtime — it is a month this
    Tempo has never heard of, and five of those in a row say nothing worth the rail's space.
    """
    months = {}
    days = [day for day in days or [] if isinstance(day, dict)]
    logged_days = [str(day.get("day") or "") for day in days if day.get("total_hours")]
    first_logged = min(logged_days, default="")

    for day in days:
        iso = str(day.get("day") or "")
        month = iso[:7]

        if len(month) != 7:
            continue

        owes = bool(first_logged) and first_logged <= iso and iso != until
        bucket = months.setdefault(month, {"month": month, "hours": 0.0, "logged": 0.0})
        bucket["hours"] += _balance(day, owes)
        bucket["logged"] += day.get("total_hours") or 0

    for bucket in months.values():
        bucket["hours"] = round(bucket["hours"], 2)
        bucket["logged"] = round(bucket["logged"], 2)

    return sorted((m for m in months.values() if m["logged"]),
                  key=lambda m: m["month"], reverse=True)


_cache = {"stamp": None, "value": None}


def summary():
    """What the rail and /api/state show, read from the tempo envelope's `year` command.

    Memoised on the envelope's stamp, because the rail is part of every page: the file is a
    year of worklogs, a hundred kilobytes that change twice a day, and a long table should
    not mean re-reading and re-adding all of it per request.

    It answers with zeros rather than raising, whatever the payload turns out to hold. The
    panel bodies have render._safe between them and the page; the rail has nothing, so an
    odd day here would take down every screen in the hub — including the settings screen,
    which is where one would go to fix the token that caused it.
    """
    try:
        info = os.stat(store.path("tempo"))
        stamp = (info.st_mtime_ns, info.st_size)
    except OSError:
        return _empty()

    if _cache["stamp"] == stamp:
        return _cache["value"]

    try:
        year = (store.read("tempo") or {}).get("payload") or {}
        year = year.get("year") if isinstance(year, dict) else None
        year = year if isinstance(year, dict) else {}
        months = by_month(year.get("days"), until=year.get("to"))
        value = {"total": round(float(sum(m["hours"] for m in months)), 2),
                 "months": months,
                 "year": str(year.get("from") or "")[:4]}
    except Exception:
        value = _empty()

    _cache.update(stamp=stamp, value=value)

    return value
