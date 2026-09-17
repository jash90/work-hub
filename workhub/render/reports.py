"""Panels whose skill needs a model to finish the job.

`commits` and `protokol` show exactly what their scripts produce on their own and hand the
rest to Claude Code through a copyable brief. The hub never invents the narrative it does
not have.
"""
from ..text import count
from .layout import chip, copy_button, empty, esc, section, table, ticket_link

COMMITS_BRIEF = """Run the daily-commit-summary skill and build an HTML report from the data
below (the `plain` field in plain words, 2-3 sentences). The data is already gathered — do
not collect it again.

=== COMMITS ===
%s

=== MERGE STATUS ===
%s
"""

# The report itself is a Polish legal document, so the phrasing it asks for stays Polish —
# only the instruction around it is in English.
PROTOKOL_BRIEF = """Run the protokol-odbioru skill for %s. The gathered items are below —
rewrite each one in the required legal phrasing („Kod źródłowy …") and fill in template.docx.

%s
"""


def commits_body(payload):
    commits = payload.get("commits") or ""
    merge = payload.get("merge") or ""

    blocks = [
        section("Commits today", '<pre class="raw">%s</pre>' % esc(commits.strip() or "No commits."),
                copy_button("Copy the brief for Claude", COMMITS_BRIEF % (commits, merge))),
        section("Merge status", '<pre class="raw">%s</pre>' % esc(merge.strip() or "No data.")),
    ]

    return "".join(blocks)


def commits_headline(payload):
    text = payload.get("commits") or ""
    lines = [l for l in text.splitlines() if " | " in l]
    repos = [l for l in text.splitlines() if l.startswith("=====")]

    return " ".join([chip(count(len(lines), "commit")),
                     chip(count(len(repos), "repository", "repositories"))])


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
        "Items for %s" % (data.get("month") or ""),
        table(["Ticket", "Product", "Platforms", "Summary"], rows) or empty("No items."),
        copy_button("Copy the brief for Claude",
                    PROTOKOL_BRIEF % (data.get("month") or "", "\n".join(brief_lines))))


def protokol_headline(payload):
    data = payload["main"]
    items = data.get("items") or []

    return " ".join([chip(data.get("month") or "—"),
                     chip(count(len(items), "item"))])
