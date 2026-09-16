"""Panel renderers: envelope payload in, HTML fragment out.

RENDERERS is the whole dispatch table — one entry per panel in sources.PANELS.
"""
from .. import links, sources, store
from . import gitlab, layout, releases, reports, tempo, work

RENDERERS = {
    "dashboard": (work.dashboard_body, work.dashboard_headline),
    "releases": (releases.body, releases.headline),
    "priority": (work.priority_body, work.priority_headline),
    "review-queue": (gitlab.queue_body, gitlab.queue_headline),
    "pr-request": (gitlab.request_body, gitlab.request_headline),
    "testing": (work.testing_body, work.testing_headline),
    "commits": (reports.commits_body, reports.commits_headline),
    "tempo": (tempo.body, tempo.headline),
    "protokol": (reports.protokol_body, reports.protokol_headline),
}


# Task-shaped panels whose own skill reports no merge request; they get the shared
# key → MR lookup so every ticket number on screen can be clicked through to its MR.
NEEDS_MR_INDEX = frozenset(("dashboard", "priority", "testing"))


def _safe(fn, payload, index=None):
    """A renderer must never take the whole page down over one odd payload."""
    try:
        return fn(payload, index) if index is not None else fn(payload)
    except Exception as exc:
        return '<div class="banner bad">Nie udało się wyrenderować panelu: %s</div>' % layout.esc(exc)


def headline(panel_id, envelope):
    payload = (envelope or {}).get("payload")

    if payload is None:
        return '<span class="muted">brak danych</span>'

    return _safe(RENDERERS[panel_id][1], payload)


def body(panel_id, envelope):
    payload = (envelope or {}).get("payload")

    if payload is None:
        return layout.empty("Panel nie ma jeszcze danych — kliknij „Odśwież”.")

    index = links.build() if panel_id in NEEDS_MR_INDEX else None

    return layout.notes(payload) + _safe(RENDERERS[panel_id][0], payload, index)


def fragment(panel_id):
    """The panel's contents alone, for swapping in after a refresh."""
    envelope = store.read(panel_id)

    return '%s%s' % (layout.banner(envelope), body(panel_id, envelope))


def _card(panel):
    envelope = store.read(panel.id)

    return """<article class="card" data-panel="%s" data-state="%s">
  <h2><a href="/p/%s">%s</a></h2>
  <p class="blurb">%s</p>
  <p class="headline">%s</p>
  <footer>
    %s
    <span class="spacer"></span>
    <button data-refresh="%s">Odśwież</button>
  </footer>
</article>""" % (panel.id, layout.state_of(envelope), panel.id, layout.esc(panel.label),
                 layout.esc(panel.blurb), headline(panel.id, envelope),
                 layout.freshness(envelope), panel.id)


def overview(hub):
    groups = []

    for group, panels in sources.grouped_panels():
        cards = "".join(_card(p) for p in panels)
        groups.append('<section class="block"><h3>%s</h3><div class="grid">%s</div></section>'
                      % (layout.esc(sources.GROUP_LABELS[group]), cards))

    schedule = " · ".join("%s: %s" % (s["label"], s["last_run"] or "jeszcze nie")
                          for s in hub.scheduler.describe())
    head = ('<div class="page-head"><h1>Przegląd</h1>'
            '<p>Ostatnie automatyczne przebiegi — %s</p></div>') % layout.esc(schedule)

    return layout.page("work-hub", "", head + "".join(groups), hub.csrf)


def panel_page(hub, panel_id):
    panel = sources.BY_ID[panel_id]
    envelope = store.read(panel_id)

    head = """<section class="panel" data-panel="%s" data-state="%s">
  <header class="panel-head">
    <h1>%s</h1>
    %s
    <span class="spacer"></span>
    %s
    <button data-refresh="%s">Odśwież</button>
  </header>
  <div data-fragment>%s</div>
</section>""" % (panel_id, layout.state_of(envelope), layout.esc(panel.label),
                 headline(panel_id, envelope), layout.freshness(envelope),
                 panel_id, fragment(panel_id))

    return layout.page("%s — work-hub" % panel.label, panel_id, head, hub.csrf)
