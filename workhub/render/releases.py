"""The release board: every fixVersion carrying one of my tasks."""
from collections import defaultdict

from ..text import count
from .layout import chip, empty, esc, notes, section, table, ticket_link

PROGRESS_TONES = {"review": "accent", "qa": "wait", "done": "ok", "mine": ""}


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


def body(payload):
    data = payload["main"]
    issues = data.get("issues") or []
    mrs = data.get("mrs") or {}
    groups = defaultdict(list)

    for issue in issues:
        groups[(issue.get("release_date") or "9999", issue.get("release_name") or "No version")].append(issue)

    blocks = [notes(payload)]

    for (date, name), items in sorted(groups.items()):
        rows = []

        for issue in items:
            rows.append([
                ticket_link(issue["key"]),
                chip(issue.get("status") or "—", PROGRESS_TONES.get(issue.get("progress"), "")),
                '<span class="repo">%s</span>' % esc(issue.get("assignee") or "—"),
                '<span class="summary">%s</span>' % esc(issue.get("summary")),
                _mr_marks(mrs.get(issue["key"])),
            ])

        when = "" if date == "9999" else " · %s" % date
        note = chip(count(len(items), "task"))
        blocks.append(section("%s%s" % (name, when),
                              table(["Ticket", "Status", "Assignee", "Summary", "MR"], rows), note))

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
