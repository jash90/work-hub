"""The Tempo panel — the only screen in the hub that can write to Jira.

Nothing here posts by itself. The month is shown one week at a time and every workday is an
editor: a day Tempo already holds opens with its own worklogs, a day it holds nothing of
opens with the proposal derived from commits. Hours move on the skill's own 15-minute grid,
the running total says whether the day may be written, and the button stays disabled until
it may — so a mistake is caught in the browser instead of coming back as the skill's
`sys.exit`. The guards that decide whether a write is legal (workday, holiday, the daily
total, a worklog id that is really there) remain the skill's.
"""
import datetime

from redge_work.polish import plural

from .layout import chip, empty, esc, link, section, table

QUARTER = 0.25
TARGET_HOURS = 8.0

WEEKDAYS = {"Mon": "poniedziałek", "Tue": "wtorek", "Wed": "środa", "Thu": "czwartek",
            "Fri": "piątek", "Sat": "sobota", "Sun": "niedziela"}

MONTHS = ("stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
          "sierpnia", "września", "października", "listopada", "grudnia")

ENDPOINTS = {"propose": "/api/tempo/log", "logged": "/api/tempo/replace"}


def _hours(value):
    return ("%g" % round(value, 2))


def _date(iso):
    day = datetime.date.fromisoformat(iso)

    return "%d %s" % (day.day, MONTHS[day.month - 1])


def _entry_row(entry):
    subjects = "\n".join("• %s" % s for s in (entry.get("subjects") or [])[:12])
    commits = entry.get("commits")

    return """<tr class="entry" data-entry%s>
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
        ' data-worklog-id="%s"' % esc(str(entry["id"])) if entry.get("id") else "",
        link("https://jira.example.com/browse/%s" % entry["key"], entry["key"], mono=True),
        esc(subjects),
        '<span class="summary">%s</span>' % esc((entry.get("summary") or "")[:90]),
        '<span class="muted">%s</span>' % esc(plural(commits, "commit", "commity", "commitów"))
        if commits is not None else "",
        esc(_hours(entry.get("hours", 0))),
        esc(entry["key"]),
    )


def _day(day, mode):
    entries = day.get("entries") or []
    weekday = WEEKDAYS.get(day.get("weekday"), day.get("weekday") or "")

    # A day Tempo already holds is cleared by writing an empty split; a day that is only a
    # proposal has nothing to clear yet, but a write made a moment ago can still be taken back.
    if entries and mode == "logged":
        trailing = '<button class="danger" data-tempo-clear>Wyczyść dzień</button>'
    elif mode == "propose":
        trailing = '<button class="danger" data-tempo-undo="%s">Cofnij</button>' % esc(day["day"])
    else:
        trailing = ""

    return """<article class="day" data-day="%s" data-target="%s" data-endpoint="%s">
  <header class="day-head">
    <div class="day-when">
      <strong>%s</strong>
      <span class="muted">%s, %s</span>
    </div>
    <span class="chip" data-total>%s h</span>
    <span class="spacer"></span>
    <label class="switch" title="Pozwól zapisać dzień krótszy niż 8 h">
      <input type="checkbox" data-partial> niepełny dzień
    </label>
    <label class="switch" title="Pozwól zapisać dzień dłuższy niż 8 h">
      <input type="checkbox" data-overtime> nadgodziny
    </label>
    <button class="primary" data-tempo-log="%s">%s</button>
    %s
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
</article>""" % (
        esc(day["day"]), TARGET_HOURS, ENDPOINTS[mode],
        esc(_date(day["day"])), esc(weekday), esc(day["day"]),
        esc(_hours(day.get("total_hours", 0))), esc(day["day"]),
        "Zapisz zmiany" if mode == "logged" else "Zaloguj dzień",
        trailing,
        "".join(_entry_row(e) for e in entries),
    )


def _rest_day(day):
    """Weekend or holiday — the skill refuses to write one, so it is shown, not edited."""
    weekday = WEEKDAYS.get(day.get("weekday"), day.get("weekday") or "")
    entries = day.get("entries") or []
    listing = "".join(
        '<li>%s <span class="muted">%s h</span></li>' % (esc(e["key"]), esc(_hours(e.get("hours", 0))))
        for e in entries)

    return """<article class="day rest">
  <header class="day-head">
    <div class="day-when"><strong>%s</strong><span class="muted">%s</span></div>
    <span class="spacer"></span>
    <span class="muted">%s</span>
  </header>%s
</article>""" % (
        esc(_date(day["day"])), esc(weekday),
        "%s h — dzień wolny, edytuj w Tempo" % esc(_hours(day.get("total_hours", 0)))
        if entries else "dzień wolny",
        '<ul class="rest-entries">%s</ul>' % listing if entries else "",
    )


def _editors(payload):
    """One editor per day: what Tempo holds, or the proposal for a day it holds nothing of.

    Two editors for the same day would mean two truths about it, and the stale one would be
    the easier to submit.
    """
    plan = {d["day"]: d for d in ((payload.get("propose") or {}).get("plan") or [])}
    out = []

    for day in ((payload.get("worklogs") or {}).get("days") or []):
        if not day.get("workday"):
            out.append((day, "rest"))
        elif day.get("entries"):
            out.append((day, "logged"))
        elif day["day"] in plan:
            out.append((plan[day["day"]], "propose"))
        else:
            out.append((day, "logged"))

    return out


def _weeks(editors):
    """Chunk the month into weeks; the range starts on a Monday, so a new week starts on one."""
    weeks = []

    for day, mode in editors:
        if datetime.date.fromisoformat(day["day"]).weekday() == 0 or not weeks:
            weeks.append([])

        weeks[-1].append((day, mode))

    return weeks


def _week(days, index, active):
    # Only what Tempo actually holds counts — a proposal is an offer, not an hour logged.
    logged = sum(d.get("total_hours", 0) for d, mode in days if mode != "propose")
    target = TARGET_HOURS * sum(1 for d, mode in days if mode != "rest")
    cards = "".join(_rest_day(d) if mode == "rest" else _day(d, mode) for d, mode in days)

    return """<section class="week" data-week="%d" data-label="%s" data-total="%s h / %s h"%s>%s</section>""" % (
        index,
        esc("%s – %s" % (_date(days[0][0]["day"]), _date(days[-1][0]["day"]))),
        esc(_hours(logged)), esc(_hours(target)),
        "" if index == active else " hidden",
        cards,
    )


def _active_week(weeks):
    today = datetime.date.today().isoformat()

    for index, days in enumerate(weeks):
        if days[0][0]["day"] <= today <= days[-1][0]["day"]:
            return index

    return len(weeks) - 1 if weeks else 0


def body(payload):
    propose = payload.get("propose") or {}
    skipped = propose.get("skipped") or []
    weeks = _weeks(_editors(payload))

    blocks = ['<div class="banner info">Zapis do Tempo następuje wyłącznie po kliknięciu '
              'i potwierdzeniu. Harmonogram o 16:00 tylko wylicza propozycje. '
              'Godziny chodzą po 15 minut; dzień poniżej 8 h wymaga „niepełnego dnia”, '
              'powyżej — „nadgodzin”.</div>']

    if weeks:
        active = _active_week(weeks)
        bar = """<div class="week-bar">
  <button type="button" class="ghost" data-week-step="-1" aria-label="poprzedni tydzień">◀</button>
  <strong data-week-label></strong>
  <span class="chip" data-week-total></span>
  <span class="spacer"></span>
  <button type="button" class="ghost" data-week-step="1" aria-label="następny tydzień">▶</button>
</div>"""
        weeks_html = "".join(_week(days, index, active) for index, days in enumerate(weeks))
        blocks.append(section(
            "Tydzień po tygodniu",
            '<div class="weeks" data-weeks data-active="%d">%s%s</div>' % (active, bar, weeks_html),
            chip(plural(len(weeks), "tydzień", "tygodnie", "tygodni"))))
    else:
        # Before the first refresh with worklogs there is nothing to lay a week over.
        plan = propose.get("plan") or []
        blocks.append(section(
            "Propozycje do zalogowania",
            "".join(_day(d, "propose") for d in plan) or empty("Nie ma dni z kompletną propozycją."),
            chip(plural(len(plan), "dzień", "dni", "dni"))))

    if skipped:
        rows = [[esc(s["day"]), '<span class="muted">%s</span>' % esc(s.get("reason"))] for s in skipped]
        blocks.append(section("Pominięte dni", table(["Dzień", "Powód"], rows), chip(str(len(skipped)))))

    blocks.append(section("Luki w Tempo",
                          '<pre class="raw">%s</pre>' % esc((payload.get("gaps") or "").strip() or "Brak.")))

    return "".join(blocks)


def headline(payload):
    plan = (payload.get("propose") or {}).get("plan") or []
    days = [d for d in ((payload.get("worklogs") or {}).get("days") or []) if d.get("workday")]
    logged = sum(d.get("total_hours", 0) for d in days)

    return " ".join([chip("%s do zalogowania" % plural(len(plan), "dzień", "dni", "dni"),
                          "wait" if plan else "ok"),
                     chip("%s h w Tempo" % _hours(logged) if days
                          else "%s h" % _hours(sum(d.get("total_hours", 0) for d in plan)))])
