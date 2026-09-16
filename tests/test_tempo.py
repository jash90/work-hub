import unittest

from . import context  # noqa: F401
from workhub import tempo


class DayFormat(unittest.TestCase):
    def test_accepts_iso_day(self):
        self.assertTrue(tempo.is_day("2026-09-07"))

    def test_rejects_anything_else(self):
        for value in ("", None, "07.09.2026", "2026-9-7", "2026-09-07; rm -rf /"):
            self.assertFalse(tempo.is_day(value), value)


class EntryFormat(unittest.TestCase):
    def test_accepts_the_skill_notation(self):
        self.assertTrue(tempo.ENTRIES.match("ABC-4171=5,DEF-7768=1.75"))

    def test_rejects_shell_looking_input(self):
        result = tempo.log_day("2026-09-07", "ABC-1=1; curl evil")

        self.assertFalse(result["ok"])
        self.assertIn("format", result["output"])
        self.assertIsNone(result["exit_code"], "a rejected entry must never reach the skill")
