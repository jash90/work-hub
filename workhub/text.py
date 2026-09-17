"""Count phrases in English.

The hub used to borrow redge_work.polish, whose three-form plural (1 task / 3 taski /
5 tasków) exists because Polish needs it. English needs two forms and a handful of
irregulars, so the rule lives here instead — one less thing the hub takes from a library
it does not ship with.
"""


def count(n, one, many=None):
    """`1 comment` / `3 comments`. Pass `many` when an -s is not the plural."""
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def days(n):
    return count(n, "day")


def days_ago(n):
    return "%s ago" % count(n, "day")
