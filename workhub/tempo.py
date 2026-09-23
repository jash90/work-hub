"""The one place in the hub that can change something outside this machine.

`tempo.py log --yes` POSTs a fresh day's worklogs to Jira; `tempo.py replace --yes` makes a
day that already has them match a given split. Every guard that matters (weekend, public
holiday, a day below or above 8 h, the 15-minute grid, a worklog id that is not really
there) already lives in the skill — the hub does not re-implement or bypass them, it just
relays what the script says. Every attempt is appended to data/write-log.jsonl.
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
# `replace` prefixes an entry Tempo already holds with its worklog id: 1404473:ABC-1=2.75.
ENTRY = r"(?:\d+:)?[A-Z][A-Z0-9]*-\d+=\d+(?:\.\d+)?"
ENTRIES = re.compile(r"^%s(?:,%s)*$" % (ENTRY, ENTRY))
TIMEOUT = 120
# The skill's own definition of a full day. It lives here rather than in a renderer because
# two screens now measure against it: the day editor and the overtime figure in the rail.
TARGET_HOURS = 8.0


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
        result = {"ok": False, "output": "could not run tempo.py: %s" % exc, "exit_code": None}

    _record(action, day, argv[2:], result)

    return result


def write_argv(action, day, entries, allow_partial=False, allow_overtime=False):
    """The exact command a write would run — built apart from running it, so it is testable."""
    argv = ["/usr/bin/python3", SCRIPT, action, day]

    if entries:
        argv += ["--entries", entries]

    argv.append("--yes")

    if allow_partial:
        argv.append("--allow-partial")

    if allow_overtime:
        argv.append("--allow-overtime")

    return argv


def log_argv(day, entries, allow_partial=False, allow_overtime=False):
    return write_argv("log", day, entries, allow_partial, allow_overtime)


def replace_argv(day, entries, allow_partial=False, allow_overtime=False):
    return write_argv("replace", day, entries, allow_partial, allow_overtime)


def write_day(action, day, entries, allow_partial=False, allow_overtime=False):
    """Run one write. `entries` is the skill's own "KEY=h,KEY=h" notation.

    Only the shape is checked here; whether the split is legal (15-minute grid, the daily
    total, a workday, a worklog id that belongs to the day) stays the skill's call.
    """
    entries = (entries or "").replace(" ", "")

    if entries and not ENTRIES.match(entries):
        return {"ok": False, "output": "bad entry format — expected KEY=h,KEY=h (hours with a dot)",
                "exit_code": None}

    return _run(action, day, write_argv(action, day, entries, allow_partial, allow_overtime))


def log_day(day, entries, allow_partial=False, allow_overtime=False):
    """Write a day that has no worklogs yet."""
    return write_day("log", day, entries, allow_partial, allow_overtime)


def replace_day(day, entries, allow_partial=False, allow_overtime=False):
    """Make a day match `entries` — the skill edits, deletes and adds to get there.

    An empty `entries` is not a missing argument here but a request to clear the day.
    """
    return write_day("replace", day, entries, allow_partial, allow_overtime)


def undo_day(day):
    return _run("undo", day, ["/usr/bin/python3", SCRIPT, "undo", day])
