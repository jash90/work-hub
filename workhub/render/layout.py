"""The page shell and the small vocabulary of bits every panel reuses."""
import datetime
import html
import re
import time

from redge_work.polish import days_phrase, plural

from .. import sources


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def chip(text, tone=""):
    return '<span class="chip %s">%s</span>' % (tone, esc(text))


def ago(seconds):
    """Relative age in Polish, at the coarsest unit that still says something useful."""
    if seconds is None:
        return "nigdy"

    delta = max(0, int(time.time() - seconds))

    if delta < 90:
        return "przed chwilą"

    minutes = delta // 60

    if minutes < 60:
        return "%s temu" % plural(minutes, "minutę", "minuty", "minut")

    hours = minutes // 60

    if hours < 24:
        return "%s temu" % plural(hours, "godzinę", "godziny", "godzin")

    days = hours // 24

    return "%s temu" % days_phrase(days)


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
        return '<time class="stamp">brak danych</time>'

    return '<time class="stamp" title="%s">%s (%s)</time>' % (
        esc(clock(envelope.get("fetched_at"))), esc(clock(envelope.get("fetched_at"))),
        esc(ago(envelope.get("fetched_at"))))


def banner(envelope):
    """A failed refresh must say so, without hiding the older data it left standing."""
    if not envelope:
        return '<div class="banner info">Panel nie był jeszcze odświeżany.</div>'

    error = envelope.get("error")

    if not error:
        return ""

    if envelope.get("payload") is None:
        return ('<div class="banner bad"><strong>Nie udało się pobrać danych.</strong> %s</div>'
                % esc(tidy_error(error)))

    return ('<div class="banner warn"><strong>Dane z %s</strong> — ostatnia próba (%s) nie powiodła się: %s</div>'
            % (esc(clock(envelope.get("fetched_at"))), esc(clock(envelope.get("attempted_at"))),
               esc(tidy_error(error))))


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


def sidebar(active):
    """Permanent left rail, grouped the same way the overview is.

    It is part of the layout, not a modal — below the narrow breakpoint it slides away
    behind the header's hamburger, because a fixed rail would eat a phone screen.
    """
    sections = []

    for group, panels in sources.grouped_panels():
        links = "".join(
            '<a href="/p/%s" class="%s">%s</a>'
            % (panel.id, "on" if active == panel.id else "", esc(panel.label))
            for panel in panels)
        sections.append('<div class="nav-group"><h4>%s</h4>%s</div>'
                        % (esc(sources.GROUP_LABELS[group]), links))

    return """<div class="scrim" data-nav-close hidden></div>
<aside class="sidebar" id="sidebar" aria-label="Nawigacja">
  <div class="sidebar-head">
    <a class="brand" href="/"><span class="dot"></span>work-hub</a>
  </div>
  <nav class="sidebar-nav">
    <a href="/" class="%s">Przegląd</a>
    %s
  </nav>
</aside>""" % ("on" if active == "" else "", "".join(sections))


# Applied before first paint so a dark theme never flashes white on load.
THEME_BOOT = ("<script>try{var t=localStorage.getItem('work-hub-theme');"
              "if(t&&t!=='auto')document.documentElement.dataset.theme=t;}catch(e){}</script>")


def crumb(active):
    panel = sources.BY_ID.get(active)

    return panel.label if panel else "Przegląd"


def page(title, active, body, csrf):
    return """<!doctype html>
<html lang="pl" data-csrf="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="/static/app.css">
%s
</head>
<body>
%s
<div class="content">
  <header class="topbar">
    <div class="topbar-inner">
      <button class="ghost icon nav-toggle" data-nav-open aria-label="Otwórz nawigację"
              aria-controls="sidebar" aria-expanded="false">☰</button>
      <h2 class="crumb">%s</h2>
      <span class="spacer"></span>
      <button class="ghost icon" data-theme-toggle title="Motyw: automatyczny" aria-label="Zmień motyw">◐</button>
      <button class="primary" data-refresh-all>Odśwież wszystko</button>
    </div>
  </header>
  <div class="page">
%s
  </div>
</div>
<div class="toast-stack" role="status" aria-live="polite"></div>
<script src="/static/day-rules.js"></script>
<script src="/static/app.js"></script>
</body>
</html>""" % (esc(csrf), esc(title), THEME_BOOT,
                 sidebar(active), esc(crumb(active)), body)


BUCKET_LABELS = {0: "Po terminie", 1: "Nadchodzące", 2: "Bez daty", 3: "Bez wersji"}
BUCKET_TONES = {0: "bad", 1: "accent", 2: "", 3: ""}


def link(url, text, mono=False):
    if not url:
        return esc(text)

    return '<a href="%s" target="_blank" rel="noopener"%s>%s</a>' % (
        esc(url), ' class="key"' if mono else "", esc(text))


def table(headers, rows):
    """`headers` are plain strings; `rows` hold ready HTML so cells can carry links."""
    if not rows:
        return ""

    head = "".join("<th>%s</th>" % esc(h) for h in headers)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in row) for row in rows)

    # Wrapped so a wide table scrolls inside its card instead of widening the whole page.
    return ('<div class="table-scroll"><table><thead><tr>%s</tr></thead><tbody>%s</tbody>'
            "</table></div>") % (head, body)


def when(row):
    """„Apple_Android TV 12.0.0 · jutro" — the release a task is aimed at."""
    name = row.get("release_name")

    if not name:
        return '<span class="muted">—</span>'

    days = row.get("days")
    parts = [esc(name)]

    if days is not None:
        if days < 0:
            parts.append('<span class="chip bad">%s po terminie</span>' % days_phrase(abs(days)))
        elif days == 0:
            parts.append('<span class="chip wait">dziś</span>')
        elif days == 1:
            parts.append('<span class="chip wait">jutro</span>')
        else:
            parts.append('<span class="chip">za %s</span>' % days_phrase(days))

    return " ".join(parts)


def mr_links(mrs):
    """`!706` chips, each a link to the merge request carrying that ticket's key."""
    out = []

    for mr in mrs or []:
        tone = ""
        detail = []

        if mr.get("approvals") is not None:
            detail.append("%d approve" % mr["approvals"])
            tone = "ok" if mr["approvals"] >= 2 else ""

        if mr.get("unresolved"):
            detail.append("%d nierozwiązane" % mr["unresolved"])
            tone = "wait"

        hint = " · ".join([x for x in (mr.get("repo"), mr.get("title")) if x] + detail)
        out.append('<a class="mr-link" href="%s" target="_blank" rel="noopener" title="%s">%s</a>'
                   % (esc(mr.get("url")), esc(hint), chip("!%s" % mr.get("iid"), tone)))

    return " ".join(out)


def notes(payload):
    """Fallback notes recorded by the runner — partial data must announce itself."""
    recorded = (payload or {}).get("_notes") or {}

    return "".join('<div class="banner warn">%s</div>' % esc(text) for text in recorded.values())


def copy_button(label, text):
    import base64

    blob = base64.b64encode(text.encode("utf-8")).decode("ascii")

    return '<button data-copy="%s">%s</button>' % (blob, esc(label))
