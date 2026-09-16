"""Envelopes: what the hub remembers about each panel between runs.

One file per panel under data/. The invariant that matters: a failed run never destroys a
good payload. Panels degrade to "stare dane + baner", never to an empty page — the skills
behind them exit hard when the VPN is down, and a blank dashboard would be a worse answer
than yesterday's.
"""
import os
import time

from redge_work import cache

from . import DATA_DIR


def path(panel_id):
    return os.path.join(DATA_DIR, "%s.json" % panel_id)


def read(panel_id):
    return cache.read_json(path(panel_id), default=None)


def write(envelope):
    cache.write_json(path(envelope["panel"]), envelope)

    return envelope


def blank(panel_id):
    return {"panel": panel_id, "payload": None, "fetched_at": None, "attempted_at": None,
            "duration_ms": None, "exit_code": None, "error": None}


def record_success(panel_id, payload, duration_ms, now=None):
    now = int(now if now is not None else time.time())
    envelope = read(panel_id) or blank(panel_id)
    envelope.update(payload=payload, fetched_at=now, attempted_at=now,
                    duration_ms=duration_ms, exit_code=0, error=None)

    return write(envelope)


def record_failure(panel_id, error, exit_code=None, duration_ms=None, now=None):
    """Keep payload and fetched_at untouched — they are the last thing that worked."""
    now = int(now if now is not None else time.time())
    envelope = read(panel_id) or blank(panel_id)
    envelope.update(attempted_at=now, duration_ms=duration_ms,
                    exit_code=exit_code, error=error)

    return write(envelope)


def is_stale(envelope):
    """True when the last attempt failed but an older payload is still on show."""
    return bool(envelope and envelope.get("error") and envelope.get("payload") is not None)
