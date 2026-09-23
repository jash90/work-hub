"""What the figure in the rail counts, and what it refuses to count.

The rule under test is one-directional: hours above eight are overtime, hours below eight
are not a debt. Every test here defends that asymmetry, because the tempting "logged minus
expected" would pass most of the same cases and answer a different question.
"""
import os
import unittest

from . import context  # noqa: F401
from workhub import overtime, store


def day(iso, hours, workday=True):
    return {"day": iso, "weekday": "Mon", "workday": workday, "total_hours": hours,
            "entries": [{"key": "ABC-1", "hours": hours}] if hours else []}


class Arithmetic(unittest.TestCase):
    def test_a_long_day_contributes_its_surplus(self):
        self.assertEqual(2.0, overtime.by_month([day("2026-09-16", 10)])[0]["hours"])

    def test_a_short_day_contributes_nothing(self):
        self.assertEqual(0.0, overtime.by_month([day("2026-09-01", 5)])[0]["hours"])

    def test_a_short_day_does_not_pay_off_a_long_one(self):
        """The rail answers "how much beyond the norm", not "did I make my hours"."""
        months = overtime.by_month([day("2026-09-16", 10), day("2026-09-01", 5)])

        self.assertEqual(2.0, months[0]["hours"])
        self.assertEqual(15.0, months[0]["logged"])

    def test_a_weekend_counts_in_full(self):
        """None of it was owed, so all of it is over the norm."""
        self.assertEqual(4.0, overtime.by_month([day("2026-09-05", 4, workday=False)])[0]["hours"])

    def test_a_day_off_with_nothing_logged_is_not_overtime(self):
        self.assertEqual([], overtime.by_month([day("2026-09-05", 0, workday=False)]))

    def test_days_are_bucketed_by_their_own_month(self):
        months = overtime.by_month([day("2026-08-31", 10), day("2026-09-01", 9)])

        self.assertEqual(["2026-09", "2026-08"], [m["month"] for m in months])
        self.assertEqual([1.0, 2.0], [m["hours"] for m in months])

    def test_the_newest_month_comes_first(self):
        months = overtime.by_month([day("2026-06-01", 9), day("2026-09-01", 9), day("2026-07-01", 9)])

        self.assertEqual(["2026-09", "2026-07", "2026-06"], [m["month"] for m in months])

    def test_a_month_with_nothing_logged_is_left_out(self):
        """Tempo starts where it starts; five empty months would say nothing in the rail."""
        months = overtime.by_month([day("2026-01-05", 0), day("2026-06-01", 9)])

        self.assertEqual(["2026-06"], [m["month"] for m in months])

    def test_nothing_at_all_is_an_empty_list(self):
        self.assertEqual([], overtime.by_month(None))
        self.assertEqual([], overtime.by_month([]))


class Envelope(unittest.TestCase):
    """summary() reads a payload it does not control, and may never raise on one.

    Panel bodies have render._safe between them and the page; the rail has nothing, so an
    exception here would take down every screen including the settings one.
    """

    def tearDown(self):
        overtime._cache.update(stamp=None, value=None)

        try:
            os.remove(store.path("tempo"))
        except OSError:
            pass

    def seed(self, payload):
        store.record_success("tempo", payload, 10, now=1000)
        overtime._cache.update(stamp=None, value=None)

    def test_it_sums_the_year_command(self):
        self.seed({"year": {"from": "2026-01-01", "to": "2026-09-22",
                            "days": [day("2026-09-16", 11), day("2026-08-12", 10)]}})

        figure = overtime.summary()

        self.assertEqual(5.0, figure["total"])
        self.assertEqual(["2026-09", "2026-08"], [m["month"] for m in figure["months"]])

    def test_the_year_is_taken_from_the_data_not_the_clock(self):
        """On 1 January the envelope still holds December's answer; the caption must match it."""
        self.seed({"year": {"from": "2025-01-01", "days": [day("2025-03-03", 9)]}})

        self.assertEqual("2025", overtime.summary()["year"])

    def test_no_envelope_means_zero_not_a_crash(self):
        self.assertEqual({"total": 0.0, "months": [], "year": ""}, overtime.summary())

    def test_a_payload_without_the_year_command_means_zero(self):
        self.seed({"worklogs": {"days": [day("2026-09-16", 11)]}})

        self.assertEqual(0.0, overtime.summary()["total"])

    def test_a_nonsense_payload_still_answers(self):
        self.seed({"year": "garbage"})

        self.assertEqual({"total": 0.0, "months": [], "year": ""}, overtime.summary())

    def test_a_day_missing_its_hours_is_survived(self):
        self.seed({"year": {"from": "2026-01-01", "days": [{"day": "2026-09-16"}, "junk"]}})

        self.assertEqual(0.0, overtime.summary()["total"])
