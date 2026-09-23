"""Overtime, summed the only way the hub can honestly sum it: one day at a time.

A day above eight hours contributes its surplus; a day below them contributes nothing. A
short Tuesday is not a debt that the following Thursday pays off — the figure in the rail
answers "how much did I work beyond the norm", not "did I make my hours", and the two
questions have different answers in every month that holds both kinds of day. A weekend or
a public holiday contributes everything logged on it, because none of it was owed.

Which days those are is never decided here. The skill already marks every day it returns
with `workday`, so the hub holds no calendar and knows no Polish holiday — it multiplies
and adds, exactly as the week totals in render/tempo.py do.

Nothing in this module filters by ticket. An hour booked on an absence or an administrative
key is an hour that was logged, and a rail that silently dropped some of them would be
answering a question nobody asked.
"""
import os

from . import store
from .tempo import TARGET_HOURS


def _empty():
    return {"total": 0.0, "months": [], "year": ""}


def _surplus(day):
    logged = day.get("total_hours") or 0

    if not day.get("workday"):
        return logged

    return max(0.0, logged - TARGET_HOURS)


def by_month(days):
    """One entry per month that holds at least one logged hour, newest first.

    A month nothing was ever logged in is not a month of zero overtime — it is a month this
    Tempo has never heard of, and five of those in a row say nothing worth the rail's space.
    """
    months = {}

    for day in days or []:
        if not isinstance(day, dict):
            continue

        month = str(day.get("day") or "")[:7]

        if len(month) != 7:
            continue

        bucket = months.setdefault(month, {"month": month, "hours": 0.0, "logged": 0.0})
        bucket["hours"] += _surplus(day)
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
        months = by_month(year.get("days"))
        value = {"total": round(float(sum(m["hours"] for m in months)), 2),
                 "months": months,
                 "year": str(year.get("from") or "")[:4]}
    except Exception:
        value = _empty()

    _cache.update(stamp=stamp, value=value)

    return value
