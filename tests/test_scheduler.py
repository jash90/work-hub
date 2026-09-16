import datetime
import unittest

from . import context  # noqa: F401
from workhub import scheduler

SCHEDULE = {"poranek": (10, 0), "popoludnie": (16, 0)}

WEDNESDAY = datetime.datetime(2026, 9, 16, 9, 0)
SATURDAY = datetime.datetime(2026, 9, 19, 17, 0)


class DueGroups(unittest.TestCase):
    def due(self, moment, state=None):
        return scheduler.due_groups(moment, state or {}, SCHEDULE)

    def test_nothing_before_the_first_target(self):
        self.assertEqual([], self.due(WEDNESDAY))

    def test_morning_after_ten(self):
        self.assertEqual(["poranek"], self.due(WEDNESDAY.replace(hour=10, minute=0)))

    def test_group_runs_once_a_day(self):
        moment = WEDNESDAY.replace(hour=14)
        self.assertEqual([], self.due(moment, {"poranek": "2026-09-16"}))

    def test_yesterdays_run_does_not_count(self):
        moment = WEDNESDAY.replace(hour=14)
        self.assertEqual(["poranek"], self.due(moment, {"poranek": "2026-09-15"}))

    def test_late_wake_catches_up_in_clock_order(self):
        """A Mac asleep until 17:00 replays the morning group first, then the afternoon one."""
        self.assertEqual(["poranek", "popoludnie"], self.due(WEDNESDAY.replace(hour=17)))

    def test_weekend_is_quiet(self):
        self.assertEqual([], self.due(SATURDAY))


class Ticking(unittest.TestCase):
    class FakeRunner:
        def __init__(self):
            self.ran = []

        def run_group(self, group):
            self.ran.append(group)

    def test_tick_runs_then_remembers(self):
        runner = self.FakeRunner()
        moment = datetime.datetime(2026, 9, 16, 11, 0)
        sched = scheduler.Scheduler(runner, clock=lambda: moment)

        scheduler.write_state({})
        self.assertEqual(["poranek"], sched.tick())
        self.assertEqual(["poranek"], runner.ran)

        self.assertEqual([], sched.tick(), "a second tick in the same day must not re-run")
        self.assertEqual(["poranek"], runner.ran)
