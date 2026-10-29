"""The page shell and the small vocabulary of bits every panel reuses."""
import datetime
import html
import json
import re
import time

from .. import config, overtime, sources, translate
from ..catalog import NOUNS, POLISH
from ..text import LANGUAGES, ago_phrase, count, days, is_polish, lang, t
from ..text import month_name as named_month


def shown(value):
    """Skill data in the page language: in Polish the skills' own text is already right."""
    text = "" if value is None else str(value)

    return text if is_polish() else translate.english(text)


def esc(value):
    """Everything written into the page passes here, so this is where skill data turns English."""
    return html.escape(shown(value), quote=True)


def chip(text, tone=""):
    return '<span class="chip %s">%s</span>' % (tone, esc(text))


def hours(value):
    """Hours as they read on screen: 8, 2.25, 7.75 — never 8.0 and never 2.2500000001."""
    return "%g" % round(value, 2)


def signed_hours(value):
    return "%+g" % round(value, 2)


def month_name(month):
    """A month key as a name: 2026-09 is September.

    The year is said once, above the list, rather than on every row of a narrow rail.
    """
    try:
        return named_month(int(month[5:7]))
    except (ValueError, IndexError):
        return month


def ago(seconds):
    """Relative age at the coarsest unit that still says something useful."""
    if seconds is None:
        return t("never")

    delta = max(0, int(time.time() - seconds))

    if delta < 90:
        return t("just now")

    minutes = delta // 60

    if minutes < 60:
        return ago_phrase(minutes, "minute")

    hours = minutes // 60

    if hours < 24:
        return ago_phrase(hours, "hour")

    return ago_phrase(hours // 24, "day")


def clock(seconds):
    if seconds is None:
        return "—"

    moment = datetime.datetime.fromtimestamp(seconds)
    today = datetime.date.today()

    if moment.date() == today:
        return moment.strftime("%H:%M")

    return moment.strftime("%d.%m %H:%M")


def freshness(envelope):
    """One line telling the truth about the data on screen."""
    if not envelope or envelope.get("payload") is None:
        return '<time class="stamp">%s</time>' % esc(t("no data"))

    return '<time class="stamp" title="%s">%s (%s)</time>' % (
        esc(clock(envelope.get("fetched_at"))), esc(clock(envelope.get("fetched_at"))),
        esc(ago(envelope.get("fetched_at"))))


def banner(envelope):
    """A failed refresh must say so, without hiding the older data it left standing."""
    if not envelope:
        return '<div class="banner info">%s</div>' % esc(t("This panel has not been refreshed yet."))

    error = envelope.get("error")

    if not error:
        return ""

    if envelope.get("payload") is None:
        return ('<div class="banner bad"><strong>%s</strong> %s</div>'
                % (esc(t("Could not fetch the data.")), esc(tidy_error(error))))

    return ('<div class="banner warn"><strong>%s</strong> — %s</div>'
            % (esc(t("Data from %s") % clock(envelope.get("fetched_at"))),
               esc(t("the last attempt (%s) failed: %s")
                   % (clock(envelope.get("attempted_at")), tidy_error(error)))))


TAGS = re.compile(r"<[^>]+>")


def tidy_error(text, limit=220):
    """Skills relay whatever the server said — sometimes a whole HTML error page."""
    plain = " ".join(TAGS.sub(" ", text or "").split())

    return plain[:limit] + ("…" if len(plain) > limit else "")


def empty(text):
    return '<p class="empty">%s</p>' % esc(text)


def section(title, body, note=""):
    head = '<h3>%s%s</h3>' % (esc(title), (" " + note) if note else "")

    return '<section class="block">%s%s</section>' % (head, body)


def state_of(envelope):
    """What a card should look like: fresh, showing older data, failed outright, or empty."""
    if not envelope or envelope.get("payload") is None:
        return "error" if (envelope or {}).get("error") else "empty"

    return "stale" if envelope.get("error") else "ok"


def rail_data():
    """The overtime figure with its months named, for the rail and for the poll behind it.

    /api/state carries this so a refresh can bring the rail up to date without a reload. The
    month names are attached here rather than in the browser: the rail already spells them
    out server-side, and a second list of twelve of them in JavaScript would be a copy free
    to drift from this one.
    """
    figure = overtime.summary()

    return dict(figure, months=[dict(month, label=month_name(month["month"]))
                                for month in figure["months"]])


def rail_figure():
    """Overtime so far this year: the total, and the months it came from.

    A figure, not navigation — hence a button and not a link. Every anchor in this rail is
    styled as a nav item, closes the drawer when tapped and counts as one more way into a
    panel, and none of that is true of a number.

    The block is rendered even with nothing in it, merely hidden, so the first Tempo run of
    a fresh hub can reveal it in place instead of waiting for the next page load.
    """
    figure = rail_data()
    rows = "".join(
        '<li><span>%s</span><span class="num">%s h</span></li>'
        % (esc(month["label"]), esc(signed_hours(month["hours"])))
        for month in figure["months"])

    return """<div class="nav-group nav-foot rail-figure" data-overtime-figure data-open="yes"%s>
      <button type="button" class="rail-total" data-overtime-fold aria-expanded="true">
        <span data-overtime-label>%s</span>
        <strong class="num" data-overtime-total>%s h</strong>
        <span class="caret">▾</span>
      </button>
      <ul class="rail-months" data-overtime-months>%s</ul>
    </div>""" % ("" if figure["months"] else " hidden",
                 esc((t("Overtime %s") % figure["year"]).strip()),
                 esc(signed_hours(figure["total"])), rows)


def sidebar(active):
    """Permanent left rail, grouped the same way the overview is.

    It is part of the layout, not a modal — below the narrow breakpoint it slides away
    behind the header's hamburger, because a fixed rail would eat a phone screen.
    """
    sections = []

    for group, panels in sources.grouped_panels():
        links = "".join(
            '<a href="/p/%s" class="%s">%s</a>'
            % (panel.id, "on" if active == panel.id else "", esc(t(panel.label)))
            for panel in panels)
        sections.append('<div class="nav-group"><h4>%s</h4>%s</div>'
                        % (esc(t(sources.GROUP_LABELS[group])), links))

    return """<div class="scrim" data-nav-close hidden></div>
<aside class="sidebar" id="sidebar" aria-label="%s">
  <div class="sidebar-head">
    <a class="brand" href="/"><span class="dot"></span>work-hub</a>
  </div>
  <nav class="sidebar-nav">
    <a href="/" class="%s">%s</a>
    %s
    <div class="nav-group nav-foot"><a href="/settings" class="%s">%s</a></div>
    %s
  </nav>
</aside>""" % (esc(t("Navigation")), "on" if active == "" else "", esc(t("Overview")),
               "".join(sections), "on" if active == "settings" else "", esc(t("Settings")),
               rail_figure())


# Applied before first paint so a dark theme never flashes white on load.
THEME_BOOT = ("<script>try{var t=localStorage.getItem('work-hub-theme');"
              "if(t&&t!=='auto')document.documentElement.dataset.theme=t;}catch(e){}</script>")


CRUMBS = {"": "Overview", "settings": "Settings"}


def crumb(active):
    panel = sources.BY_ID.get(active)

    return t(panel.label if panel else CRUMBS.get(active, "Overview"))


def strings_for_browser():
    """The Polish catalogue for app.js, embedded only when the page is Polish.

    One source for both sides of the wire: the browser reads the same table `t()` does.
    """
    if not is_polish():
        return ""

    blob = json.dumps({"strings": POLISH, "nouns": NOUNS}, ensure_ascii=False)

    return "<script>window.WORK_HUB_STRINGS = %s;</script>" % blob.replace("</", "<\\/")


def language_toggle():
    """Names the language a click switches to, as language pickers conventionally do."""
    other = [code for code in LANGUAGES if code != lang()][0]

    return ('<button class="ghost icon" data-lang="%s" title="%s" aria-label="%s">%s</button>'
            % (other, html.escape(t("Switch to English") if is_polish() else "Przełącz na polski"),
               esc(t("Change language")), other.upper()))


def page(title, active, body, csrf):
    return """<!doctype html>
<html lang="%s" data-csrf="%s" data-jira="%s" data-keys="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="/static/app.css">
%s
%s
</head>
<body>
%s
<div class="content">
  <header class="topbar">
    <div class="topbar-inner">
      <button class="ghost icon nav-toggle" data-nav-open aria-label="%s"
              aria-controls="sidebar" aria-expanded="false">☰</button>
      <h2 class="crumb">%s</h2>
      <span class="spacer"></span>
      %s
      <button class="ghost icon" data-theme-toggle title="%s" aria-label="%s">◐</button>
      <button class="primary" data-refresh-all>%s</button>
    </div>
  </header>
  <div class="page">
%s
  </div>
</div>
<div class="toast-stack" role="status" aria-live="polite"></div>
<script src="/static/i18n.js"></script>
<script src="/static/day-rules.js"></script>
<script src="/static/app.js"></script>
</body>
</html>""" % (lang(), esc(csrf), esc(config.jira_base_url()), esc(",".join(config.project_keys())),
                 esc(title), THEME_BOOT, strings_for_browser(), sidebar(active),
                 esc(t("Open navigation")), esc(crumb(active)), language_toggle(),
                 esc(t("Theme: automatic")), esc(t("Change theme")), esc(t("Refresh all")), body)


BUCKET_LABELS = {0: "Overdue", 1: "Upcoming", 2: "No date", 3: "No version"}
BUCKET_TONES = {0: "bad", 1: "accent", 2: "", 3: ""}


def link(url, text, mono=False):
    if not url:
        return esc(text)

    return '<a href="%s" target="_blank" rel="noopener"%s>%s</a>' % (
        esc(url), ' class="key"' if mono else "", esc(text))


def ticket_link(key):
    """A ticket number, linked when an address is configured and plain text when it is not.

    The address is the hub's own setting: it decides where a key points on screen, not which
    Jira the skills query — that host lives in redge_work, outside this repository.
    """
    base = config.jira_base_url()

    return link("%s/browse/%s" % (base, key) if base else "", key, mono=True)


def version_link(key, version_id, name):
    """A fixVersion name, linked to its page in the project of `key`, one of its tickets."""
    base = config.jira_base_url()
    project = key.split("-")[0]

    return link("%s/projects/%s/versions/%s" % (base, project, version_id)
                if base and version_id else "", name)


def table(headers, rows):
    """`headers` are plain English strings, put into the page language here; `rows` hold
    ready HTML so cells can carry links."""
    if not rows:
        return ""

    head = "".join("<th>%s</th>" % esc(t(h)) for h in headers)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in row) for row in rows)

    # Wrapped so a wide table scrolls inside its card instead of widening the whole page.
    return ('<div class="table-scroll"><table><thead><tr>%s</tr></thead><tbody>%s</tbody>'
            "</table></div>") % (head, body)


def when(row):
    """"Apple_Android TV 12.0.0 · tomorrow" — the release a task is aimed at."""
    name = row.get("release_name")

    if not name:
        return '<span class="muted">—</span>'

    left = row.get("days")
    parts = [esc(name)]

    if left is not None:
        if left < 0:
            parts.append(chip(t("%s overdue") % days(abs(left)), "bad"))
        elif left == 0:
            parts.append(chip(t("today"), "wait"))
        elif left == 1:
            parts.append(chip(t("tomorrow"), "wait"))
        else:
            parts.append(chip(t("in %s") % days(left)))

    return " ".join(parts)


def mr_links(mrs):
    """`!706` chips, each a link to the merge request carrying that ticket's key."""
    out = []

    for mr in mrs or []:
        tone = ""
        detail = []

        if mr.get("approvals") is not None:
            detail.append(t("%d approve") % mr["approvals"])
            tone = "ok" if mr["approvals"] >= 2 else ""

        if mr.get("unresolved"):
            detail.append(count(mr["unresolved"], "unresolved thread"))
            tone = "wait"

        hint = " · ".join([x for x in (mr.get("repo"), mr.get("title")) if x] + detail)
        out.append('<a class="mr-link" href="%s" target="_blank" rel="noopener" title="%s">%s</a>'
                   % (esc(mr.get("url")), esc(hint), chip("!%s" % mr.get("iid"), tone)))

    return " ".join(out)


def notes(payload):
    """Fallback notes recorded by the runner — partial data must announce itself."""
    recorded = (payload or {}).get("_notes") or {}

    return "".join('<div class="banner warn">%s</div>' % esc(t(text)) for text in recorded.values())


def copy_button(label, text):
    import base64

    blob = base64.b64encode(text.encode("utf-8")).decode("ascii")

    return '<button data-copy="%s">%s</button>' % (blob, esc(label))
