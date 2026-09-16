"""The Tempo day rules live in JavaScript; Node runs them so they are tested, not assumed."""
import json
import os
import shutil
import subprocess
import unittest

from . import context  # noqa: F401
from workhub import ROOT

RULES = os.path.join(ROOT, "workhub", "static", "day-rules.js")

DRIVER = """
const {dayVerdict, parseHours, round15} = require(%s);
const cases = JSON.parse(process.argv[1]);
const out = cases.map((c) => {
  if (c.kind === 'parse') return parseHours(c.raw);
  if (c.kind === 'round') return round15(c.value);
  return dayVerdict(c.hours.map((h) => (h === 'zle' ? parseHours('abc') : h)), c.target, c.partial);
});
process.stdout.write(JSON.stringify(out));
"""


def node_run(cases):
    driver = DRIVER % json.dumps(RULES)
    proc = subprocess.run(["node", "-e", driver, json.dumps(cases)],
                          capture_output=True, text=True, timeout=30)

    if proc.returncode != 0:
        raise AssertionError(proc.stderr)

    return json.loads(proc.stdout)


@unittest.skipUnless(shutil.which("node"), "node nie jest zainstalowany")
class DayVerdict(unittest.TestCase):
    def verdict(self, hours, target=8, partial=False):
        return node_run([{"kind": "day", "hours": hours, "target": target, "partial": partial}])[0]

    def test_a_full_day_may_be_written(self):
        verdict = self.verdict([5, 1.75, 1.25])

        self.assertTrue(verdict["ok"])
        self.assertEqual(8, verdict["total"])

    def test_a_short_day_is_blocked_and_says_how_short(self):
        verdict = self.verdict([5, 1.75])

        self.assertFalse(verdict["ok"])
        self.assertIn("brakuje 1.25 h", verdict["problem"])

    def test_a_short_day_passes_when_marked_partial(self):
        verdict = self.verdict([6], partial=True)

        self.assertTrue(verdict["ok"])
        self.assertIn("niepełny dzień", verdict["note"])

    def test_hours_off_the_fifteen_minute_grid_are_blocked(self):
        """The skill exits on this; catching it in the browser saves a round trip."""
        verdict = self.verdict([1.1, 6.9])

        self.assertFalse(verdict["ok"])
        self.assertIn("15 minut", verdict["problem"])

    def test_an_empty_day_is_blocked(self):
        self.assertIn("przynajmniej jedną", self.verdict([])["problem"])

    def test_unparsable_hours_are_blocked(self):
        self.assertIn("liczbą", self.verdict(["zle", 8])["problem"])

    def test_many_quarters_still_add_up_exactly(self):
        """Floating point: 32 x 0.25 must read as 8, not 7.999999999999999."""
        verdict = self.verdict([0.25] * 32)

        self.assertTrue(verdict["ok"])
        self.assertEqual(8, verdict["total"])


@unittest.skipUnless(shutil.which("node"), "node nie jest zainstalowany")
class ParsingHours(unittest.TestCase):
    def parse(self, raw):
        return node_run([{"kind": "parse", "raw": raw}])[0]

    def test_a_polish_decimal_comma_is_accepted(self):
        self.assertEqual(1.75, self.parse("1,75"))

    def test_a_dot_is_accepted(self):
        self.assertEqual(1.75, self.parse("1.75"))

    def test_blank_means_zero(self):
        self.assertEqual(0, self.parse("  "))

    def test_nonsense_is_not_silently_zero(self):
        self.assertIsNone(self.parse("abc"), "NaN survives as null through JSON")
        self.assertIsNone(self.parse("-2"))

    def test_rounding_lands_on_the_grid(self):
        self.assertEqual([1.25, 0, 2.0], node_run([
            {"kind": "round", "value": 1.2}, {"kind": "round", "value": -5},
            {"kind": "round", "value": 1.9}]))
