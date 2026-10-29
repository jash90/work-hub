"""The interface language: English by default, Polish on request.

The language belongs to one request — the `lang` cookie read by the server — and lives in a
context variable, so a renderer never takes it as an argument and two browser tabs on
different languages never see each other's. English is the source text: `t()` looks a phrase
up in the Polish catalogue and hands it back unchanged in English, or when no entry exists.

Counting differs in kind, not just in words. English has two forms; Polish has three
(1 task / 3 taski / 5 tasków), which redge_work.polish already knows how to choose.
"""
import contextvars
import datetime

from redge_work.polish import plural

from .catalog import AGO_NOUNS, NOUNS, POLISH

ENGLISH = "en"
POLISH_LANG = "pl"
LANGUAGES = (ENGLISH, POLISH_LANG)

_lang = contextvars.ContextVar("lang", default=ENGLISH)

MONTHS = {
    ENGLISH: ("January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"),
    POLISH_LANG: ("Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec",
                  "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"),
}

WEEKDAYS = {
    ENGLISH: ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    POLISH_LANG: ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"),
}

SHORT_WEEKDAYS = {
    ENGLISH: ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    POLISH_LANG: ("pn", "wt", "śr", "czw", "pt", "sob", "nd"),
}


def lang():
    return _lang.get()


def use(code):
    """Switch the current request to `code`; anything unknown falls back to English."""
    _lang.set(code if code in LANGUAGES else ENGLISH)


def is_polish():
    return lang() == POLISH_LANG


def t(text):
    return POLISH.get(text, text) if is_polish() else text


def count(n, one, many=None):
    """`1 comment` / `3 comments`. Pass `many` when an -s is not the plural."""
    if is_polish() and one in NOUNS:
        return plural(n, *NOUNS[one])

    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def days(n):
    return count(n, "day")


def days_ago(n):
    if is_polish():
        return "od %s" % ("%d dnia" % n if n == 1 else "%d dni" % n)

    return "%s ago" % count(n, "day")


def ago_phrase(n, unit):
    """`5 minutes ago` / `5 minut temu` — Polish puts the unit in the accusative here."""
    if is_polish():
        return "%s temu" % plural(n, *AGO_NOUNS[unit])

    return "%s ago" % count(n, unit)


def month_name(index):
    """`index` is 1-based, as in a date."""
    return MONTHS[lang()][index - 1]


def weekday(day, short=False):
    return (SHORT_WEEKDAYS if short else WEEKDAYS)[lang()][day.weekday()]


def short_date(iso):
    """`Wed 28.10` / `śr 28.10` — the day a block of commits belongs to."""
    day = datetime.date.fromisoformat(iso)

    return "%s %s" % (weekday(day, short=True), day.strftime("%d.%m"))
