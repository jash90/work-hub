"""The release board: every fixVersion carrying one of my tasks."""
from collections import defaultdict

from redge_work.polish import plural

from .layout import chip, empty, esc, link, notes, section, table

PROGRESS_TONES = {"review": "accent", "qa": "wait", "done": "ok", "mine": ""}


def _mr_marks(mrs):
    marks = []

    for mr in mrs or []:
        tone = "ok" if mr.get("approval_count", 0) >= 2 else ""
        label = "!%s (%d approve" % (mr.get("iid"), mr.get("approval_count", 0))

        if mr.get("unresolved"):
            label += ", %d nierozwiązane" % mr["unresolved"]

        marks.append('<a href="%s" target="_blank" rel="noopener">%s</a>'
                     % (esc(mr.get("web_url")), chip(label + ")", tone)))

    return " ".join(marks)


def body(payload):
    data = payload["main"]
    issues = data.get("issues") or []
    mrs = data.get("mrs") or {}
    groups = defaultdict(list)

    for issue in issues:
        groups[(issue.get("release_date") or "9999", issue.get("release_name") or "Bez wersji")].append(issue)

    blocks = [notes(payload)]

    for (date, name), items in sorted(groups.items()):
        rows = []

        for issue in items:
            rows.append([
                link("https://jira.example.com/browse/%s" % issue["key"], issue["key"], mono=True),
                chip(issue.get("status") or "—", PROGRESS_TONES.get(issue.get("progress"), "")),
                '<span class="muted">%s</span>' % esc(issue.get("assignee") or "—"),
                '<span class="summary">%s</span>' % esc(issue.get("summary")),
                _mr_marks(mrs.get(issue["key"])),
            ])

        when = "" if date == "9999" else " · %s" % date
        note = chip("%s" % plural(len(items), "task", "taski", "tasków"))
        blocks.append(section("%s%s" % (name, when),
                              table(["Ticket", "Status", "Przypisany", "Temat", "MR"], rows), note))

    history = data.get("history") or []

    if history:
        rows = [[esc(h.get("ts", "").replace("T", " ")[:16]),
                 link("https://jira.example.com/browse/%s" % h["key"], h["key"], mono=True),
                 '<span class="muted">%s → </span>%s' % (esc(h.get("from")), chip(h.get("to") or ""))]
                for h in history[:25]]
        blocks.append(section("Zmiany statusów", table(["Kiedy", "Ticket", "Przejście"], rows),
                              chip(str(len(history)))))

    return "".join(blocks) or empty("Brak tasków w wydaniach.")


def headline(payload):
    data = payload["main"]
    issues = data.get("issues") or []
    releases = {i.get("release_name") for i in issues if i.get("release_name")}

    return " ".join([chip(plural(len(releases), "wydanie", "wydania", "wydań")),
                     chip(plural(len(issues), "task", "taski", "tasków"))])
