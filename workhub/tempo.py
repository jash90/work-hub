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
# The skill parses hours with float(), so a decimal comma would crash it — only a dot passes.
ENTRY = r"[A-Z][A-Z0-9]*-\d+=\d+(?:\.\d+)?"
ENTRIES = re.compile(r"^%s(?:,%s)*$" % (ENTRY, ENTRY))
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


def log_argv(day, entries, allow_partial=False):
    """The exact command a write would run — built apart from running it, so it is testable."""
    argv = ["/usr/bin/python3", SCRIPT, "log", day]

    if entries:
        argv += ["--entries", entries]

    argv.append("--yes")

    if allow_partial:
        argv.append("--allow-partial")

    return argv


def log_day(day, entries, allow_partial=False):
    """POST one day's worklogs. `entries` is the skill's own "KEY=h,KEY=h" notation.

    Only the shape is checked here; whether the split is legal (15-minute grid, 8 h total,
    a workday that is not already logged) stays the skill's call.
    """
    entries = (entries or "").replace(" ", "")

    if entries and not ENTRIES.match(entries):
        return {"ok": False, "output": "zły format wpisów — oczekiwane KEY=h,KEY=h (godziny z kropką)",
                "exit_code": None}

    return _run("log", day, log_argv(day, entries, allow_partial))


def undo_day(day):
    return _run("undo", day, ["/usr/bin/python3", SCRIPT, "undo", day])
