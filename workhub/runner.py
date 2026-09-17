"""Runs a panel's skill scripts and turns the result into an envelope.

Panels run one at a time, deliberately. Four of them read the same
~/.claude/cache/mr-index.json (TTL 300 s); firing them in parallel would make each one ask
GitLab separately instead of hitting the cache the first panel just filled.
"""
import json
import subprocess
import threading
import time

from . import sources, store

# glab lives in homebrew and two skills shell out to it; launchd hands us a PATH without it.
PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

STDERR_TAIL = 500


def _env():
    """What every skill subprocess inherits: the process environment, then `.env` over it.

    os.environ itself is never touched, so a token saved in the settings view reaches the
    next panel run without a restart and without the hub carrying a secret in memory.
    """
    import os

    from . import config

    env = dict(os.environ)
    env.update(config.load())
    env["PATH"] = PATH

    return env


def _tail(text):
    text = (text or "").strip()

    return text[-STDERR_TAIL:] if text else ""


class CommandFailed(Exception):
    pass


def run_command(command, timeout, env=None):
    """Execute one command and parse its stdout. Raises CommandFailed with a human message."""
    argv = command.resolve()

    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env=env if env is not None else _env())
    except subprocess.TimeoutExpired:
        raise CommandFailed("przekroczony czas %ds (%s)" % (timeout, command.name))
    except OSError as exc:
        raise CommandFailed("nie udało się uruchomić %s: %s" % (command.name, exc))

    if proc.returncode != 0:
        detail = _tail(proc.stderr) or _tail(proc.stdout) or "brak komunikatu"
        raise CommandFailed("%s zakończone kodem %d: %s" % (command.name, proc.returncode, detail))

    if command.parse == sources.TEXT:
        return proc.stdout

    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise CommandFailed("%s nie zwróciło JSON-a: %s" % (command.name, _tail(proc.stdout)[:200]))


class Runner:
    """Shared by the HTTP server and the scheduler, so a click and a tick cannot collide."""

    def __init__(self):
        self._locks = {p.id: threading.Lock() for p in sources.PANELS}
        self._running = set()
        self._guard = threading.Lock()

    def is_running(self, panel_id):
        with self._guard:
            return panel_id in self._running

    def running(self):
        with self._guard:
            return set(self._running)

    def run_panel(self, panel_id):
        """Run one panel. Returns its envelope, or None when a run was already in flight."""
        panel = sources.BY_ID[panel_id]
        lock = self._locks[panel_id]

        if not lock.acquire(blocking=False):
            return None

        with self._guard:
            self._running.add(panel_id)

        started = time.time()

        try:
            payload = {}
            notes = {}

            for command in panel.commands:
                try:
                    payload[command.name] = run_command(command, panel.timeout)
                except CommandFailed as exc:
                    if not command.fallback:
                        raise

                    payload[command.name] = run_command(command.fallback, panel.timeout)
                    notes[command.name] = command.fallback_note or str(exc)

            if notes:
                payload["_notes"] = notes

            elapsed = int((time.time() - started) * 1000)

            return store.record_success(panel_id, payload, elapsed)
        except CommandFailed as exc:
            elapsed = int((time.time() - started) * 1000)

            return store.record_failure(panel_id, str(exc), duration_ms=elapsed)
        finally:
            with self._guard:
                self._running.discard(panel_id)

            lock.release()

    def run_group(self, group):
        return [self.run_panel(p.id) for p in sources.group_panels(group)]

    def run_all(self):
        return [self.run_panel(p.id) for p in sources.PANELS]
