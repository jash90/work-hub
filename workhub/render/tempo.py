"""The Tempo panel — the only screen in the hub that can write to Jira.

Nothing here posts by itself. Each day carries its proposal, an editable entry field and a
button that asks for confirmation before the hub runs `tempo.py log --yes`. The skill's own
guards (weekend, holiday, day already logged, total != 8 h) stay in charge; we show what
they say.
"""
from redge_work.polish import plural

from .layout import chip, empty, esc, link, section, table


def _entries_value(entry_list):
    return ",".join("%s=%s" % (e["key"], ("%g" % e["hours"])) for e in entry_list)


def _day_rows(plan):
    rows = []

    for day in plan:
        entries = day.get("entries") or []
        detail = "<br>".join(
            '%s <span class="muted">%g h · %s</span>' % (
                link("https://jira.example.com/browse/%s" % e["key"], e["key"], mono=True),
                e["hours"], esc((e.get("summary") or "")[:70]))
            for e in entries)
        value = _entries_value(entries)
        total = day.get("total_hours", 0)

        rows.append([
            '<strong>%s</strong><br><span class="muted">%s</span>' % (esc(day["day"]), esc(day.get("weekday"))),
            detail or '<span class="muted">—</span>',
            chip("%g h" % total, "ok" if total == 8 else "wait"),
            ('<input class="entries" value="%s" data-entries="%s">' % (esc(value), esc(day["day"]))),
            ('<button class="primary" data-tempo-log="%s">Zaloguj dzień</button> '
             '<button class="danger" data-tempo-undo="%s">Cofnij</button>') % (esc(day["day"]), esc(day["day"])),
        ])

    return rows


def body(payload):
    propose = payload.get("propose") or {}
    plan = propose.get("plan") or []
    skipped = propose.get("skipped") or []

    blocks = ['<div class="banner info">Zapis do Tempo następuje wyłącznie po kliknięciu '
              'i potwierdzeniu. Harmonogram o 16:00 tylko wylicza propozycje.</div>']

    blocks.append(section(
        "Propozycje do zalogowania",
        table(["Dzień", "Propozycja", "Suma", "Wpisy (edytowalne)", ""], _day_rows(plan))
        or empty("Nie ma dni z kompletną propozycją."),
        chip(plural(len(plan), "dzień", "dni", "dni"))))

    if skipped:
        rows = [[esc(s["day"]), '<span class="muted">%s</span>' % esc(s.get("reason"))] for s in skipped]
        blocks.append(section("Pominięte dni", table(["Dzień", "Powód"], rows), chip(str(len(skipped)))))

    blocks.append(section("Luki w Tempo",
                          '<pre class="raw">%s</pre>' % esc((payload.get("gaps") or "").strip() or "Brak.")))

    return "".join(blocks)


def headline(payload):
    propose = payload.get("propose") or {}
    plan = propose.get("plan") or []
    hours = sum(d.get("total_hours", 0) for d in plan)

    return " ".join([chip("%s do zalogowania" % plural(len(plan), "dzień", "dni", "dni"),
                          "wait" if plan else "ok"),
                     chip("%g h" % hours)])
