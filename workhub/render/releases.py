"""The release board: every fixVersion carrying one of my tasks."""
from collections import defaultdict

from ..text import count
from .layout import chip, empty, esc, notes, section, table, ticket_link

PROGRESS_TONES = {"review": "accent", "qa": "wait", "done": "ok", "mine": ""}

# The skill's own bucket for a task nobody will touch again — it covers Done and Rejected
# alike, which is why the rule below reads it rather than matching status names.
CLOSED = "closed"


def _mr_marks(mrs):
    marks = []

    for mr in mrs or []:
        tone = "ok" if mr.get("approval_count", 0) >= 2 else ""
        label = "!%s (%d approve" % (mr.get("iid"), mr.get("approval_count", 0))

        if mr.get("unresolved"):
            label += ", %s" % count(mr["unresolved"], "unresolved thread")

        marks.append('<a href="%s" target="_blank" rel="noopener">%s</a>'
                     % (esc(mr.get("web_url")), chip(label + ")", tone)))

    return " ".join(marks)


def _warnings(data):
    """The skill says when a release could not be expanded; a board silently missing a
    team roster looks complete, which is worse than one that admits the gap."""
    said = (data.get("meta") or {}).get("warnings") or []

    return "".join('<div class="banner warn">%s</div>' % esc(w) for w in said)


def finished_reason(items):
    """Why a release needs no more of my attention, or "" while it still does.

    The test is on my own tasks, not the release as a whole: a release where my one ticket
    was rejected is over for me even with twenty of the team's still open. A release I have
    nothing in is never called finished — there is no work of mine to be done with.
    """
    mine = [i for i in items if i.get("mine")]

    if not mine or any(i.get("progress") != CLOSED for i in mine):
        return ""

    others_open = [i for i in items if not i.get("mine") and i.get("progress") != CLOSED]

    if not others_open:
        return "every task closed"

    return "my tasks closed · %s still open for the team" % count(len(others_open), "task")


def _release(name, when, items, mrs):
    rows = []

    for issue in items:
        rows.append([
            ticket_link(issue["key"]),
            chip(issue.get("status") or "—", PROGRESS_TONES.get(issue.get("progress"), "")),
            '<span class="repo">%s</span>' % esc(issue.get("assignee") or "—"),
            '<span class="summary">%s</span>' % esc(issue.get("summary")),
            _mr_marks(mrs.get(issue["key"])),
        ])

    reason = finished_reason(items)

    return """<section class="block release" data-release="%s"%s>
  <h3>
    <button type="button" class="ghost release-fold" data-release-fold aria-expanded="true"
            aria-label="fold this release">▾</button>
    <span class="release-name">%s</span><span class="muted">%s</span>
    %s%s
  </h3>
  <div class="release-body">%s</div>
</section>""" % (
        esc(name), ' data-finished="%s"' % esc(reason) if reason else "",
        esc(name), esc(when),
        chip(count(len(items), "task")),
        ' <span class="muted finished-why">%s</span>' % esc(reason) if reason else "",
        table(["Ticket", "Status", "Assignee", "Summary", "MR"], rows),
    )


def body(payload):
    data = payload["main"]
    issues = data.get("issues") or []
    mrs = data.get("mrs") or {}
    groups = defaultdict(list)

    for issue in issues:
        groups[(issue.get("release_date") or "9999", issue.get("release_name") or "No version")].append(issue)

    blocks = [notes(payload), _warnings(data)]
    finished = sum(1 for items in groups.values() if finished_reason(items))

    if groups:
        blocks.append("""<div class="release-bar" data-release-bar>
  <span class="muted" data-fold-count>%s</span>
  <span class="spacer"></span>
  <button type="button" class="ghost" data-fold-all="yes">Fold all</button>
  <button type="button" class="ghost" data-fold-all="no">Unfold all</button>
</div>""" % esc("%s folded as finished" % count(finished, "release") if finished else ""))

    for (date, name), items in sorted(groups.items()):
        blocks.append(_release(name, "" if date == "9999" else " · %s" % date, items, mrs))

    history = data.get("history") or []

    if history:
        rows = [[esc(h.get("ts", "").replace("T", " ")[:16]),
                 ticket_link(h["key"]),
                 '<span class="muted">%s → </span>%s' % (esc(h.get("from")), chip(h.get("to") or ""))]
                for h in history[:25]]
        blocks.append(section("Status changes", table(["When", "Ticket", "Transition"], rows),
                              chip(str(len(history)))))

    return "".join(blocks) or empty("No tasks in any release.")


def headline(payload):
    data = payload["main"]
    issues = data.get("issues") or []
    releases = {i.get("release_name") for i in issues if i.get("release_name")}

    return " ".join([chip(count(len(releases), "release")),
                     chip(count(len(issues), "task"))])
