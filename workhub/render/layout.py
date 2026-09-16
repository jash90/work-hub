"""The page shell and the small vocabulary of bits every panel reuses."""
import datetime
import html
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
        return '<div class="banner bad"><strong>Nie udało się pobrać danych.</strong> %s</div>' % esc(error)

    return ('<div class="banner warn"><strong>Dane z %s</strong> — ostatnia próba (%s) nie powiodła się: %s</div>'
            % (esc(clock(envelope.get("fetched_at"))), esc(clock(envelope.get("attempted_at"))), esc(error)))


def empty(text):
    return '<p class="empty">%s</p>' % esc(text)


def section(title, body, note=""):
    head = '<h3>%s%s</h3>' % (esc(title), (" " + note) if note else "")

    return '<section class="block">%s%s</section>' % (head, body)


def nav(active):
    links = ['<a href="/" class="%s">Przegląd</a>' % ("on" if active == "" else "")]

    for panel in sources.PANELS:
        links.append('<a href="/p/%s" class="%s">%s</a>' % (
            panel.id, "on" if active == panel.id else "", esc(panel.label)))

    return '<nav class="tabs">%s</nav>' % "".join(links)


def page(title, active, body, csrf):
    return """<!doctype html>
<html lang="pl" data-csrf="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
<div class="page">
<header class="top">
  <h1>work-hub</h1>
  %s
  <span class="spacer"></span>
  <button class="primary" data-refresh-all>Odśwież wszystko</button>
</header>
%s
</div>
<script src="/static/app.js"></script>
</body>
</html>""" % (esc(csrf), esc(title), nav(active), body)


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

    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (head, body)


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


def notes(payload):
    """Fallback notes recorded by the runner — partial data must announce itself."""
    recorded = (payload or {}).get("_notes") or {}

    return "".join('<div class="banner warn">%s</div>' % esc(text) for text in recorded.values())


def copy_button(label, text):
    import base64

    blob = base64.b64encode(text.encode("utf-8")).decode("ascii")

    return '<button data-copy="%s">%s</button>' % (blob, esc(label))
