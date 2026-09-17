"""The 10:00 / 16:00 refresh, run from inside the server process.

Catch-up, not cron: a group is due when the target time has passed today and the group has
not run today yet. A Mac asleep until 14:00 therefore runs the morning group once on wake
instead of losing it — which is why this lives here rather than in extra launchd agents.
"""
import datetime
import os
import threading
import time

from redge_work import cache

from . import DATA_DIR, config, sources

STATE = os.path.join(DATA_DIR, "schedule-state.json")
TICK_SECONDS = 60

TARGETS = {
    sources.MORNING: (10, 0),
    sources.AFTERNOON: (16, 0),
}


def _override(group, default):
    """WORK_HUB_MORNING=10:00 / WORK_HUB_AFTERNOON=16:30, from `.env` or the environment.

    Read once at start-up: the scheduler runs in this process, not as a subprocess, so a
    change takes effect on the next restart rather than the next tick.
    """
    raw = config.get("WORK_HUB_%s" % group.upper())

    if not raw or ":" not in raw:
        return default

    hour, _, minute = raw.partition(":")

    try:
        return int(hour), int(minute)
    except ValueError:
        return default


def targets():
    return {group: _override(group, default) for group, default in TARGETS.items()}


def read_state():
    return cache.read_json(STATE, default={}) or {}


def write_state(state):
    cache.write_json(STATE, state)


def due_groups(now, state, schedule=None):
    """Which groups should run at `now` (a datetime), given what already ran."""
    if now.weekday() >= 5:
        return []

    today = now.date().isoformat()
    due = []

    # chronological, so a wake-up at 17:00 replays the morning group before the afternoon one
    for group, (hour, minute) in sorted((schedule or targets()).items(), key=lambda kv: kv[1]):
        if state.get(group) == today:
            continue

        if (now.hour, now.minute) >= (hour, minute):
            due.append(group)

    return due


class Scheduler:
    def __init__(self, runner, clock=datetime.datetime.now):
        self.runner = runner
        self.clock = clock
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # a scheduler that dies silently is worse than one that skips
                pass

            self._stop.wait(TICK_SECONDS)

    def tick(self):
        """Run whatever is due and remember it. Returns the groups it ran."""
        now = self.clock()
        state = read_state()
        ran = []

        for group in due_groups(now, state):
            self.runner.run_group(group)
            state[group] = now.date().isoformat()
            write_state(state)
            ran.append(group)

        return ran

    def describe(self):
        state = read_state()
        schedule = targets()

        return [{"group": group, "label": sources.GROUP_LABELS[group],
                 "at": "%02d:%02d" % schedule[group], "last_run": state.get(group)}
                for group in sorted(schedule)]
