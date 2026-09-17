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


class ReplaceCommand(unittest.TestCase):
    """Editing a day that Tempo already holds — the same argv, a different subcommand."""

    def test_the_wanted_split_is_passed_to_replace(self):
        argv = tempo.replace_argv("2026-09-08", "1404473:ABC-1=2.5,DEF-2=5.5")

        self.assertEqual(["replace", "2026-09-08", "--entries",
                          "1404473:ABC-1=2.5,DEF-2=5.5", "--yes"], argv[2:])

    def test_an_existing_worklog_may_be_addressed_by_id(self):
        self.assertTrue(tempo.ENTRIES.match("1404473:ABC-1=2.75,DEF-2=5.25"))

    def test_clearing_a_day_sends_no_entries(self):
        self.assertEqual(["replace", "2026-09-08", "--yes"], tempo.replace_argv("2026-09-08", "")[2:])

    def test_a_worklog_id_never_smuggles_a_shell_string(self):
        result = tempo.replace_day("2026-09-08", "1404473; curl evil:ABC-1=8")

        self.assertFalse(result["ok"])
        self.assertIsNone(result["exit_code"], "a rejected entry must never reach the skill")


class WriteCommand(unittest.TestCase):
    """The argv a write would run, checked without ever running it."""

    def test_entries_and_confirmation_are_passed(self):
        argv = tempo.log_argv("2026-09-07", "ABC-1=8")

        self.assertEqual(["log", "2026-09-07", "--entries", "ABC-1=8", "--yes"], argv[2:])

    def test_partial_day_is_opt_in(self):
        self.assertNotIn("--allow-partial", tempo.log_argv("2026-09-07", "ABC-1=6"))
        self.assertIn("--allow-partial", tempo.log_argv("2026-09-07", "ABC-1=6", allow_partial=True))

    def test_overtime_is_its_own_opt_in(self):
        """--allow-partial no longer covers both directions, so it must not be sent for 9 h."""
        argv = tempo.log_argv("2026-09-07", "ABC-1=9", allow_overtime=True)

        self.assertIn("--allow-overtime", argv)
        self.assertNotIn("--allow-partial", argv)

    def test_quarter_hours_survive_the_round_trip(self):
        self.assertIn("ABC-1=1.75,DEF-2=6.25",
                      tempo.log_argv("2026-09-07", "ABC-1=1.75,DEF-2=6.25"))

    def test_a_decimal_comma_never_reaches_the_skill(self):
        """tempo.py parses hours with float(), which would crash on "1,75"."""
        result = tempo.log_day("2026-09-07", "ABC-1=1,75")

        self.assertFalse(result["ok"])
        self.assertIsNone(result["exit_code"])
