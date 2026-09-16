"""Panels answering „co mam do zrobienia": dashboard, priority, testing."""
from redge_work.polish import days_ago_phrase, plural

from .layout import (BUCKET_LABELS, BUCKET_TONES, chip, empty, esc, link, section, table, when)

REVIEW_LABELS = {
    "waiting_for_me": "czeka na moją odpowiedź",
    "ignored": "bez odzewu",
    "no_reply": "świeże, bez odpowiedzi",
    "fixed": "poprawione",
    "answered": "odpowiedziano",
    "resolved_by_me": "zamknięte przeze mnie",
}


def _mr_links(mrs):
    return " ".join(link(m.get("web_url"), "!%s" % m.get("iid"), mono=True) for m in mrs or [])


def _task_rows(rows):
    out = []

    for row in rows:
        out.append([
            link("https://jira.example.com/browse/%s" % row["key"], row["key"], mono=True),
            chip(row.get("status") or "—"),
            when(row),
            '<span class="summary">%s</span>' % esc(row.get("summary")),
            _mr_links(row.get("mrs")),
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
            marks.append(chip("%s" % plural(mr["unresolved"], "wątek", "wątki", "wątków"), "wait"))

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
            '<span class="muted">%s</span>' % esc("od %s" % days_ago_phrase(waited) if waited is not None else ""),
        ])

    return out


def dashboard_body(payload):
    data = payload["main"]
    blocks = []

    tasks = data.get("tasks") or []
    blocks.append(section(
        "Do zrobienia", table(["Ticket", "Status", "Wydanie", "Temat", "MR"], _task_rows(tasks))
        or empty("Nic nie czeka na start."),
        chip(str(len(tasks)))))

    ready = data.get("ready") or []
    blocks.append(section(
        "Gotowe do mergu",
        table(["MR", "Repo", "Tytuł", "Stan", "Blokady"], _mr_rows(ready, data.get("min_approvals", 2)))
        or empty("Żaden z moich MR-ów nie zebrał jeszcze kompletu approve."),
        chip(str(len(ready)), "ok" if ready else "")))

    others = data.get("other_mrs") or []
    blocks.append(section(
        "Pozostałe moje MR-y",
        table(["MR", "Repo", "Tytuł", "Stan", "Blokady"], _mr_rows(others, data.get("min_approvals", 2)))
        or empty("Brak innych otwartych MR-ów."),
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
        body.append(section("Czekają na mnie", table(
            ["MR", "Repo", "Miejsce", "Treść", "Czeka"], _review_rows(mine)) or empty("Nic."), ""))
        body.append(section("Czekają na autora", table(
            ["MR", "Repo", "Miejsce", "Treść", "Czeka"], _review_rows(stuck[:20])) or empty("Nic."), ""))

        blocks.append(section(
            "Moje uwagi w cudzych MR-ach", "".join(body),
            chip("%d w %s" % (summary.get("total", 0),
                              plural(summary.get("mrs", 0), "MR-ze", "MR-ach", "MR-ach")))))

    drift = data.get("drift") or []

    if drift:
        rows = [[link(d.get("url"), d.get("label"), mono=True), chip(d.get("status") or "—"),
                 '<span class="summary">%s</span>' % esc(d.get("detail"))] for d in drift]
        blocks.append(section("Rozjazd Jira ↔ GitLab",
                              table(["Ticket", "Status", "Co zrobić"], rows), chip(str(len(drift)), "wait")))

    return "".join(blocks)


def dashboard_headline(payload):
    data = payload["main"]
    review = (data.get("review") or {}).get("summary") or {}

    return " ".join([
        chip("%s do zrobienia" % plural(len(data.get("tasks") or []), "task", "taski", "tasków")),
        chip("%s do mergu" % plural(len(data.get("ready") or []), "MR gotowy", "MR-y gotowe", "MR-ów gotowych"),
             "ok" if data.get("ready") else ""),
        chip("%s u mnie" % plural(review.get("on_me", 0), "uwaga", "uwagi", "uwag"),
             "wait" if review.get("on_me") else ""),
    ])


def priority_body(payload):
    data = payload["main"]
    issues = data.get("issues") or []
    blocks = []

    for bucket in sorted({i.get("bucket", 3) for i in issues}):
        rows = [i for i in issues if i.get("bucket", 3) == bucket]
        blocks.append(section(
            BUCKET_LABELS.get(bucket, "Inne"),
            table(["Ticket", "Status", "Wydanie", "Temat", ""], _task_rows(rows)),
            chip(str(len(rows)), BUCKET_TONES.get(bucket, ""))))

    return "".join(blocks) or empty("Brak nierozwiązanych tasków.")


def priority_headline(payload):
    issues = payload["main"].get("issues") or []
    overdue = len([i for i in issues if i.get("bucket") == 0])

    return " ".join([chip(plural(len(issues), "task", "taski", "tasków")),
                     chip("%d po terminie" % overdue, "bad" if overdue else "")])


def _queried_status(payload):
    jql = payload["main"].get("jql") or ""
    _, _, rest = jql.partition('CHANGED TO "')

    return rest.partition('"')[0] or "Internal testing"


def testing_body(payload):
    data = payload["main"]
    status = _queried_status(payload)
    issues = data.get("issues") or []
    still = [i for i in issues if i.get("status") == status]
    moved = [i for i in issues if i.get("status") != status]

    def rows(items):
        return [[link("https://jira.example.com/browse/%s" % i["key"], i["key"], mono=True),
                 chip(i.get("status") or "—", "ok" if i.get("resolution") else ""),
                 '<span class="repo">%s</span>' % esc(i.get("assignee") or "—"),
                 '<span class="summary">%s</span>' % esc(i.get("summary"))] for i in items]

    return "".join([
        section("Nadal w „%s”" % status, table(["Ticket", "Status", "Przypisany", "Temat"], rows(still))
                or empty("Nic nie czeka."), chip(str(len(still)), "wait" if still else "")),
        section("Poszły dalej", table(["Ticket", "Status", "Przypisany", "Temat"], rows(moved[:40]))
                or empty("Nic."), chip(str(len(moved)), "ok")),
    ])


def testing_headline(payload):
    data = payload["main"]
    status = _queried_status(payload)
    issues = data.get("issues") or []
    still = len([i for i in issues if i.get("status") == status])

    return " ".join([chip("%s do testów" % plural(len(issues), "ticket", "tickety", "ticketów")),
                     chip("%d nadal w testach" % still, "wait" if still else "ok")])
