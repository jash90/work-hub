"""Panels answering "what have I got to do": dashboard, priority, testing."""
from ..links import merge
from ..text import count, days_ago
from .layout import (BUCKET_LABELS, BUCKET_TONES, chip, empty, esc, link, mr_links, section,
                     table, ticket_link, when)

REVIEW_LABELS = {
    "waiting_for_me": "waiting on my reply",
    "ignored": "no response",
    "no_reply": "fresh, no reply yet",
    "fixed": "fixed",
    "answered": "answered",
    "resolved_by_me": "closed by me",
}


def _task_rows(rows, index=None):
    """`index` fills in the MR for panels whose own skill never reports one."""
    index = index or {}
    out = []

    for row in rows:
        mrs = merge(row.get("mrs"), index.get(row["key"]))
        out.append([
            ticket_link(row["key"]),
            chip(row.get("status") or "—"),
            when(row),
            '<span class="summary">%s</span>' % esc(row.get("summary")),
            mr_links(mrs),
        ])

    return out


def _mr_rows(mrs, min_approvals):
    out = []

    for mr in mrs:
        flags = list(mr.get("blocking") or [])
        marks = [chip("%d/%d approve" % (mr.get("approval_count", 0), min_approvals),
                      "ok" if mr.get("approval_count", 0) >= min_approvals else "")]

        if mr.get("draft"):
            marks.append(chip("draft", "wait"))

        if mr.get("unresolved"):
            marks.append(chip(count(mr["unresolved"], "thread"), "wait"))

        out.append([
            link(mr.get("web_url"), "!%s" % mr.get("iid"), mono=True),
            '<span class="repo">%s</span>' % esc(mr.get("repo")),
            '<span class="summary">%s</span>' % esc(mr.get("title")),
            " ".join(marks),
            '<span class="muted">%s</span>' % esc(", ".join(flags)) if flags else "",
        ])

    return out


def _review_rows(threads):
    out = []

    for thread in threads:
        where = "%s:%s" % (thread.get("file") or "?", thread.get("line") or "?")
        waited = thread.get("waited_days")
        out.append([
            link(thread.get("url"), "!%s" % thread.get("iid"), mono=True),
            '<span class="repo">%s</span>' % esc(thread.get("repo")),
            '<span class="key">%s</span>' % esc(where),
            '<span class="summary">%s</span>' % esc((thread.get("excerpt") or "")[:220]),
            '<span class="muted">%s</span>' % esc(days_ago(waited) if waited is not None else ""),
        ])

    return out


def dashboard_body(payload, index=None):
    data = payload["main"]
    blocks = []

    tasks = data.get("tasks") or []
    blocks.append(section(
        "To do", table(["Ticket", "Status", "Release", "Summary", "MR"], _task_rows(tasks, index))
        or empty("Nothing waiting to be started."),
        chip(str(len(tasks)))))

    ready = data.get("ready") or []
    blocks.append(section(
        "Ready to merge",
        table(["MR", "Repo", "Title", "State", "Blockers"], _mr_rows(ready, data.get("min_approvals", 2)))
        or empty("None of my MRs has a full set of approvals yet."),
        chip(str(len(ready)), "ok" if ready else "")))

    others = data.get("other_mrs") or []
    blocks.append(section(
        "My other MRs",
        table(["MR", "Repo", "Title", "State", "Blockers"], _mr_rows(others, data.get("min_approvals", 2)))
        or empty("No other open MRs."),
        chip(str(len(others)))))

    review = data.get("review") or {}
    summary = review.get("summary") or {}
    threads = review.get("threads") or []

    if summary:
        counts = summary.get("counts") or {}
        marks = " ".join(chip("%s: %d" % (REVIEW_LABELS.get(k, k), v),
                              "wait" if k == "waiting_for_me" else "")
                         for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
        mine = [t for t in threads if t.get("kind") == "waiting_for_me"]
        stuck = [t for t in threads if t.get("kind") in ("ignored", "no_reply")]

        body = ['<p class="headline">%s</p>' % marks]
        body.append(section("Waiting on me", table(
            ["MR", "Repo", "Where", "Comment", "Waiting"], _review_rows(mine)) or empty("Nothing."), ""))
        body.append(section("Waiting on the author", table(
            ["MR", "Repo", "Where", "Comment", "Waiting"], _review_rows(stuck[:20])) or empty("Nothing."), ""))

        blocks.append(section(
            "My comments on other people's MRs", "".join(body),
            chip("%d across %s" % (summary.get("total", 0), count(summary.get("mrs", 0), "MR")))))

    drift = data.get("drift") or []

    if drift:
        rows = [[link(d.get("url"), d.get("label"), mono=True), chip(d.get("status") or "—"),
                 '<span class="summary">%s</span>' % esc(d.get("detail"))] for d in drift]
        blocks.append(section("Jira ↔ GitLab drift",
                              table(["Ticket", "Status", "What to do"], rows), chip(str(len(drift)), "wait")))

    return "".join(blocks)


def dashboard_headline(payload):
    data = payload["main"]
    review = (data.get("review") or {}).get("summary") or {}

    return " ".join([
        chip("%s to do" % count(len(data.get("tasks") or []), "task")),
        chip("%s ready to merge" % count(len(data.get("ready") or []), "MR"),
             "ok" if data.get("ready") else ""),
        chip("%s on me" % count(review.get("on_me", 0), "comment"),
             "wait" if review.get("on_me") else ""),
    ])


def priority_body(payload, index=None):
    data = payload["main"]
    issues = data.get("issues") or []
    blocks = []

    for bucket in sorted({i.get("bucket", 3) for i in issues}):
        rows = [i for i in issues if i.get("bucket", 3) == bucket]
        blocks.append(section(
            BUCKET_LABELS.get(bucket, "Other"),
            table(["Ticket", "Status", "Release", "Summary", "MR"], _task_rows(rows, index)),
            chip(str(len(rows)), BUCKET_TONES.get(bucket, ""))))

    return "".join(blocks) or empty("No unresolved tasks.")


def priority_headline(payload):
    issues = payload["main"].get("issues") or []
    overdue = len([i for i in issues if i.get("bucket") == 0])

    return " ".join([chip(count(len(issues), "task")),
                     chip("%d overdue" % overdue, "bad" if overdue else "")])


def _queried_status(payload):
    jql = payload["main"].get("jql") or ""
    _, _, rest = jql.partition('CHANGED TO "')

    return rest.partition('"')[0] or "Internal testing"


def testing_body(payload, index=None):
    data = payload["main"]
    index = index or {}
    status = _queried_status(payload)
    issues = data.get("issues") or []
    still = [i for i in issues if i.get("status") == status]
    moved = [i for i in issues if i.get("status") != status]

    def rows(items):
        return [[ticket_link(i["key"]),
                 chip(i.get("status") or "—", "ok" if i.get("resolution") else ""),
                 '<span class="repo">%s</span>' % esc(i.get("assignee") or "—"),
                 '<span class="summary">%s</span>' % esc(i.get("summary")),
                 mr_links(index.get(i["key"]))] for i in items]

    headers = ["Ticket", "Status", "Assignee", "Summary", "MR"]

    return "".join([
        section("Still in “%s”" % status, table(headers, rows(still))
                or empty("Nothing waiting."), chip(str(len(still)), "wait" if still else "")),
        section("Moved on", table(headers, rows(moved[:40]))
                or empty("Nothing."), chip(str(len(moved)), "ok")),
    ])


def testing_headline(payload):
    data = payload["main"]
    status = _queried_status(payload)
    issues = data.get("issues") or []
    still = len([i for i in issues if i.get("status") == status])

    return " ".join([chip("%s in testing" % count(len(issues), "ticket")),
                     chip("%d still there" % still, "wait" if still else "ok")])
