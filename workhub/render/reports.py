"""Panels whose skill needs a model to finish the job.

`commits` and `protokol` show exactly what their scripts produce on their own and hand the
rest to Claude Code through a copyable brief. The hub never invents the narrative it does
not have.
"""
from redge_work.polish import plural

from .layout import chip, copy_button, empty, esc, link, section, table

COMMITS_BRIEF = """Odpal skill daily-commit-summary i zbuduj z poniższych danych raport HTML
(pole `plain` po ludzku, 2-3 zdania). Dane są już zebrane, nie zbieraj ich ponownie.

=== COMMITY ===
%s

=== STATUS MERGE ===
%s
"""

PROTOKOL_BRIEF = """Odpal skill protokol-odbioru za miesiąc %s. Poniżej zebrane pozycje —
przepisz każdą na wymagany język prawniczy („Kod źródłowy …") i wypełnij template.docx.

%s
"""


def commits_body(payload):
    commits = payload.get("commits") or ""
    merge = payload.get("merge") or ""

    blocks = [
        section("Commity dnia", '<pre class="raw">%s</pre>' % esc(commits.strip() or "Brak commitów."),
                copy_button("Skopiuj brief dla Claude", COMMITS_BRIEF % (commits, merge))),
        section("Status merge", '<pre class="raw">%s</pre>' % esc(merge.strip() or "Brak danych.")),
    ]

    return "".join(blocks)


def commits_headline(payload):
    text = payload.get("commits") or ""
    lines = [l for l in text.splitlines() if " | " in l]
    repos = [l for l in text.splitlines() if l.startswith("=====")]

    return " ".join([chip(plural(len(lines), "commit", "commity", "commitów")),
                     chip("%s" % plural(len(repos), "repozytorium", "repozytoria", "repozytoriów"))])


def protokol_body(payload):
    data = payload["main"]
    items = data.get("items") or []
    rows = []

    for item in items:
        rows.append([
            link("https://jira.example.com/browse/%s" % item["ticket"], item["ticket"], mono=True),
            esc(item.get("product") or "—"),
            '<span class="muted">%s</span>' % esc(", ".join(item.get("platforms") or [])),
            '<span class="summary">%s</span>' % esc(item.get("jira_summary")),
        ])

    brief_lines = ["- %s (%s, %s): %s" % (i["ticket"], i.get("product"),
                                          ", ".join(i.get("platforms") or []), i.get("jira_summary"))
                   for i in items]

    return section(
        "Pozycje miesiąca %s" % (data.get("month") or ""),
        table(["Ticket", "Produkt", "Platformy", "Temat"], rows) or empty("Brak pozycji."),
        copy_button("Skopiuj brief dla Claude",
                    PROTOKOL_BRIEF % (data.get("month") or "", "\n".join(brief_lines))))


def protokol_headline(payload):
    data = payload["main"]
    items = data.get("items") or []

    return " ".join([chip(data.get("month") or "—"),
                     chip(plural(len(items), "pozycja", "pozycje", "pozycji"))])
