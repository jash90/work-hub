"""Panels about merge requests: the review queue and the review-request post."""
from redge_work.polish import plural

from .layout import chip, copy_button, empty, esc, link, section, table

STATE_TONES = {"nowy": "accent", "re-review": "wait"}


def queue_body(payload):
    data = payload["main"]
    rows = []

    for item in data.get("queue") or []:
        marks = [chip(item.get("state") or "", STATE_TONES.get(item.get("state"), ""))]

        if item.get("open_threads"):
            marks.append(chip(plural(item["open_threads"], "wątek", "wątki", "wątków"), "wait"))

        if item.get("draft"):
            marks.append(chip("draft"))

        rows.append([
            link(item.get("web_url"), "!%s" % item.get("iid"), mono=True),
            '<span class="muted">%s</span>' % esc(item.get("project", "").split("/")[-1]),
            esc(item.get("version_name") or "—"),
            '<span class="muted">%s</span>' % esc(item.get("author")),
            '<span class="summary">%s</span>' % esc(item.get("title")),
            " ".join(marks),
        ])

    blocks = [section("Kolejka", table(
        ["MR", "Repo", "Wydanie", "Autor", "Tytuł", "Stan"], rows)
        or empty("Kolejka pusta — nie ma czego reviewować."), chip(str(len(rows))))]

    skipped = data.get("skipped") or []

    if skipped:
        srows = [[link(s.get("web_url"), "!%s" % s.get("iid"), mono=True),
                  '<span class="muted">%s</span>' % esc(s.get("project", "").split("/")[-1]),
                  '<span class="summary">%s</span>' % esc(s.get("title")),
                  '<span class="muted">%s</span>' % esc(s.get("reason"))] for s in skipped]
        blocks.append(section("Pominięte", table(["MR", "Repo", "Tytuł", "Powód"], srows),
                              chip(str(len(skipped)))))

    scanned = data.get("scanned") or {}

    if scanned:
        srows = [[esc(project), str(counts.get("open", 0)), str(counts.get("kolejka", 0)),
                  str(counts.get("moje", 0)), str(counts.get("pominiete", 0))]
                 for project, counts in scanned.items()]
        blocks.append(section("Przeskanowane repozytoria",
                              table(["Repo", "Otwartych", "W kolejce", "Moich", "Pominiętych"], srows)))

    return "".join(blocks)


def queue_headline(payload):
    data = payload["main"]
    queue = data.get("queue") or []
    fresh = len([q for q in queue if q.get("state") == "nowy"])

    return " ".join([chip("%s w kolejce" % plural(len(queue), "MR", "MR-y", "MR-ów")),
                     chip("%d nowych" % fresh, "accent" if fresh else "")])


def request_body(payload):
    data = payload["main"]
    mrs = data.get("merge_requests") or []
    blocks = []

    if payload.get("post"):
        blocks.append(section(
            "Gotowy post", '<pre class="raw">%s</pre>' % esc(payload["post"]),
            copy_button("Skopiuj post", payload["post"])))

    rows = []

    for mr in mrs:
        marks = [chip("%d approve" % mr.get("approvals", 0), "ok" if mr.get("approvals") else "")]

        if mr.get("unresolved"):
            marks.append(chip(plural(mr["unresolved"], "wątek", "wątki", "wątków"), "wait"))

        rows.append([
            link(mr.get("url"), "!%s" % mr.get("iid"), mono=True),
            '<span class="muted">%s</span>' % esc(mr.get("project", "").split("/")[-1]),
            esc(mr.get("version_name") or "—"),
            '<span class="summary">%s</span>' % esc(mr.get("title")),
            chip(mr.get("jira_status") or "—"),
            " ".join(marks),
        ])

    blocks.append(section("Moje MR-y bez kompletu approve",
                          table(["MR", "Repo", "Wydanie", "Tytuł", "Jira", "Stan"], rows)
                          or empty("Wszystkie moje MR-y mają komplet approve."),
                          chip(str(len(rows)))))

    return "".join(blocks)


def request_headline(payload):
    mrs = payload["main"].get("merge_requests") or []
    none_yet = len([m for m in mrs if not m.get("approvals")])

    return " ".join([chip("%s czeka" % plural(len(mrs), "MR", "MR-y", "MR-ów")),
                     chip("%d bez approve" % none_yet, "wait" if none_yet else "")])
