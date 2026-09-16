"""The one place in the hub that can change something outside this machine.

`tempo.py log --yes` POSTs worklogs to Jira. Every guard that matters (weekend, public
holiday, a day that already has worklogs, a total that is not 8 h, the 15-minute grid)
already lives in the skill — the hub does not re-implement or bypass them, it just relays
what the script says. Every attempt is appended to data/write-log.jsonl.
"""
import json
import os
import re
import subprocess
import time

from . import DATA_DIR, sources
from .runner import PATH, _env

SCRIPT = sources.skill("tempo-fill", "tempo.py")
WRITE_LOG = os.path.join(DATA_DIR, "write-log.jsonl")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ENTRIES = re.compile(r"^[A-Z][A-Z0-9]*-\d+=\d+(?:[.,]\d+)?(?:,[A-Z][A-Z0-9]*-\d+=\d+(?:[.,]\d+)?)*$")
TIMEOUT = 120


def is_day(value):
    return bool(value and DAY.match(value))


def _record(action, day, argv, result):
    os.makedirs(DATA_DIR, exist_ok=True)
    line = {"at": int(time.time()), "action": action, "day": day,
            "argv": argv, "ok": result["ok"], "output": result["output"][-800:]}

    with open(WRITE_LOG, "a") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def _run(action, day, argv):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT, env=_env())
        output = (proc.stdout or "") + (proc.stderr or "")
        result = {"ok": proc.returncode == 0, "output": output.strip(), "exit_code": proc.returncode}
    except (OSError, subprocess.SubprocessError) as exc:
        result = {"ok": False, "output": "nie udało się uruchomić tempo.py: %s" % exc, "exit_code": None}

    _record(action, day, argv[2:], result)

    return result


def log_day(day, entries):
    """POST one day's worklogs. `entries` is the skill's own "KEY=h,KEY=h" notation."""
    if entries and not ENTRIES.match(entries.replace(" ", "")):
        return {"ok": False, "output": "zły format wpisów — oczekiwane KEY=h,KEY=h", "exit_code": None}

    argv = ["/usr/bin/python3", SCRIPT, "log", day, "--yes"]

    if entries:
        argv[4:4] = ["--entries", entries.replace(" ", "")]

    return _run("log", day, argv)


def undo_day(day):
    return _run("undo", day, ["/usr/bin/python3", SCRIPT, "undo", day])
