"""Report-shaped panels.

`commits` renders daily-commit-summary's own JSON, prose included: the skill writes it with
`claude -p` and caches it per row. `protokol` still hands its legal rewrite to Claude Code
through a copyable brief — the hub never invents prose it has not got.
"""
from ..text import count, short_date, t
from .layout import chip, copy_button, empty, esc, mr_links, section, table, ticket_link

# The report itself is a Polish legal document, so the phrasing it asks for stays Polish —
# only the instruction around it is in English.
PROTOKOL_BRIEF = """Run the protokol-odbioru skill for %s. The gathered items are below —
rewrite each one in the required legal phrasing („Kod źródłowy …") and fill in template.docx.

%s
"""


# daily-commit-summary decides the state and its tone; the hub only puts it into words.
COMMIT_STATES = {
    "merged": "on develop",
    "merged_elsewhere": "merged",
    "release": "on a release branch only",
    "draft": "draft MR",
    "ready": "ready for review",
    "followup_draft": "follow-up · draft MR",
    "followup_ready": "follow-up · ready for review",
    "abandoned": "MR closed",
    "no_mr": "pushed, no MR",
    "local": "not pushed",
}

TONE_CHIPS = {"ok": "ok", "wait": "wait", "build": "build", "neutral": ""}


def _with_code(text):
    """The skill's prose is plain text that may wrap identifiers in <code>; nothing else passes."""
    return esc(text).replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")


def _commit_row(row):
    mr = row.get("mr")
    tickets = "<br>".join(ticket_link(key) for key in row["tickets"])
    subjects = "\n".join(c["subject"] for c in row["commits"])
    status = chip(t(COMMIT_STATES.get(row["state"], row["state"])), TONE_CHIPS.get(row["tone"], ""))
    where = (mr_links([{"iid": mr["iid"], "url": mr["web_url"], "title": mr.get("title")}])
             if mr else '<span class="muted key">%s</span>' % esc(row.get("ref")))

    return [
        '%s<br><span class="muted" title="%s">%s</span>'
        % (tickets, esc(subjects), esc(count(len(row["commits"]), "commit"))),
        '<div class="summary">%s</div><p class="muted">%s</p>'
        % (_with_code(row["scope"]), esc(row["plain"])),
        "%s %s" % (status, where),
    ]


def _commit_rows(payload):
    return [row for repo_day in payload["main"]["sections"] for row in repo_day["rows"]]


def commits_body(payload):
    data = payload.get("main")

    if not data:
        return empty(t("This panel's data predates the current report format — click “Refresh”."))

    blocks = []

    for repo_day in data["sections"]:
        blocks.append(section(
            "%s · %s" % (short_date(repo_day["day"]), repo_day["repo"]),
            table(["Ticket", "What changed", "Status"], [_commit_row(r) for r in repo_day["rows"]]),
            '<span class="muted">%s</span>' % esc(count(repo_day["commits"], "commit"))))

    return "".join(blocks) or empty(t("No commits in the last 30 days."))


def commits_headline(payload):
    if not payload.get("main"):
        return '<span class="muted">%s</span>' % esc(t("refresh needed"))

    rows = _commit_rows(payload)
    tickets = sum(len(r["tickets"]) for r in rows)
    merged = sum(len(r["tickets"]) for r in rows if r["tone"] == "ok")
    waiting = sum(len(r["tickets"]) for r in rows if r["tone"] == "wait")
    commits = sum(repo_day["commits"] for repo_day in payload["main"]["sections"])

    return " ".join([chip(count(commits, "commit")),
                     chip(count(tickets, "ticket")),
                     chip(t("%d on develop") % merged, "ok" if merged else ""),
                     chip(t("%d waiting") % waiting, "wait" if waiting else "")])


def protokol_body(payload):
    data = payload["main"]
    items = data.get("items") or []
    rows = []

    for item in items:
        rows.append([
            ticket_link(item["ticket"]),
            esc(item.get("product") or "—"),
            '<span class="muted">%s</span>' % esc(", ".join(item.get("platforms") or [])),
            '<span class="summary">%s</span>' % esc(item.get("jira_summary")),
        ])

    brief_lines = ["- %s (%s, %s): %s" % (i["ticket"], i.get("product"),
                                          ", ".join(i.get("platforms") or []), i.get("jira_summary"))
                   for i in items]

    return section(
        t("Items for %s") % (data.get("month") or ""),
        table(["Ticket", "Product", "Platforms", "Summary"], rows) or empty(t("No items.")),
        copy_button(t("Copy the brief for Claude"),
                    PROTOKOL_BRIEF % (data.get("month") or "", "\n".join(brief_lines))))


def protokol_headline(payload):
    data = payload["main"]
    items = data.get("items") or []

    return " ".join([chip(data.get("month") or "—"),
                     chip(count(len(items), "item"))])
