"""The Tempo panel — the only screen in the hub that can write to Jira.

Nothing here posts by itself. Each day is an editor: hours move on the skill's own
15-minute grid, the running total says whether the day adds up, and the button stays
disabled until it does — so a mistake is caught in the browser instead of coming back as
the skill's `sys.exit`. The guards that decide whether a write is legal (workday, holiday,
a day already logged) remain the skill's.
"""
from redge_work.polish import plural

from .layout import chip, empty, esc, link, section, table

QUARTER = 0.25
TARGET_HOURS = 8.0

WEEKDAYS = {"Mon": "poniedziałek", "Tue": "wtorek", "Wed": "środa", "Thu": "czwartek",
            "Fri": "piątek", "Sat": "sobota", "Sun": "niedziela"}


def _hours(value):
    return ("%g" % round(value, 2))


def _entry_row(entry):
    subjects = "\n".join("• %s" % s for s in (entry.get("subjects") or [])[:12])
    commits = entry.get("commits") or 0

    return """<tr class="entry" data-entry>
  <td class="entry-key">%s</td>
  <td class="entry-summary" title="%s">%s</td>
  <td class="entry-commits">%s</td>
  <td class="entry-hours">
    <div class="stepper">
      <button type="button" class="step" data-step="-0.25" aria-label="mniej o 15 minut">−</button>
      <input type="text" class="hours" value="%s" inputmode="decimal"
             autocomplete="off" aria-label="godziny dla %s">
      <button type="button" class="step" data-step="0.25" aria-label="więcej o 15 minut">+</button>
    </div>
  </td>
  <td class="entry-drop">
    <button type="button" class="ghost" data-drop aria-label="usuń pozycję">×</button>
  </td>
</tr>""" % (
        link("https://jira.example.com/browse/%s" % entry["key"], entry["key"], mono=True),
        esc(subjects),
        '<span class="summary">%s</span>' % esc((entry.get("summary") or "")[:90]),
        '<span class="muted">%s</span>' % esc(plural(commits, "commit", "commity", "commitów")),
        esc(_hours(entry.get("hours", 0))),
        esc(entry["key"]),
    )


def _day(day):
    entries = day.get("entries") or []
    total = day.get("total_hours", 0)
    weekday = WEEKDAYS.get(day.get("weekday"), day.get("weekday") or "")

    rows = "".join(_entry_row(e) for e in entries)

    return """<article class="day" data-day="%s" data-target="%s">
  <header class="day-head">
    <div class="day-when">
      <strong>%s</strong>
      <span class="muted">%s</span>
    </div>
    <span class="chip" data-total>%s h</span>
    <span class="spacer"></span>
    <label class="switch" title="Pozwól zapisać dzień, który nie sumuje się do 8 h">
      <input type="checkbox" data-partial> niepełny dzień
    </label>
    <button class="primary" data-tempo-log="%s">Zaloguj dzień</button>
    <button class="danger" data-tempo-undo="%s">Cofnij</button>
  </header>
  <table class="entries-table"><tbody>%s</tbody></table>
  <div class="add-entry">
    <input class="add-key" placeholder="ABC-1234" aria-label="klucz ticketu"
           pattern="[A-Za-z][A-Za-z0-9]*-[0-9]+">
    <div class="stepper">
      <button type="button" class="step" data-step="-0.25" aria-label="mniej o 15 minut">−</button>
      <input type="text" class="hours add-hours" value="1" inputmode="decimal"
             autocomplete="off" aria-label="godziny nowej pozycji">
      <button type="button" class="step" data-step="0.25" aria-label="więcej o 15 minut">+</button>
    </div>
    <button type="button" data-add>Dodaj pozycję</button>
    <span class="spacer"></span>
    <span class="muted hint" data-hint></span>
  </div>
</article>""" % (esc(day["day"]), TARGET_HOURS, esc(day["day"]), esc(weekday),
                 esc(_hours(total)), esc(day["day"]), esc(day["day"]), rows)


def body(payload):
    propose = payload.get("propose") or {}
    plan = propose.get("plan") or []
    skipped = propose.get("skipped") or []

    blocks = ['<div class="banner info">Zapis do Tempo następuje wyłącznie po kliknięciu '
              'i potwierdzeniu. Harmonogram o 16:00 tylko wylicza propozycje. '
              'Godziny chodzą po 15 minut; dzień musi sumować się do 8 h, chyba że '
              'zaznaczysz „niepełny dzień”.</div>']

    days = "".join(_day(d) for d in plan)

    blocks.append(section(
        "Propozycje do zalogowania", days or empty("Nie ma dni z kompletną propozycją."),
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
                     chip("%s h" % _hours(hours))])
