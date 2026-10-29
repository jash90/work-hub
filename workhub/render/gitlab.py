"""Panels about merge requests: the review queue and the review-request post."""
from collections import Counter

from ..text import count, t
from .layout import attr, chip, copy_button, empty, esc, link, section, shown, table

STATE_TONES = {"nowy": "accent", "re-review": "wait"}


# The queue's own vocabulary for how much attention an MR needs. The keys are the skill's
# own values and stay in its language; only what is shown is translated.
STATE_PICK_LABELS = {"nowy": "new", "re-review": "re-review"}


def _pick_box(item):
    return ('<input type="checkbox" class="pick" data-url="%s" data-state="%s"'
            ' aria-label="%s">'
            % (attr(item.get("web_url")), attr(item.get("state") or ""),
               esc(t("select MR !%s") % item.get("iid"))))


def _picker(items):
    """One toggle for everything, plus one per state so a whole kind can be picked at once."""
    counts = Counter(item.get("state") for item in items if item.get("state"))
    toggles = ['<label class="switch"><input type="checkbox" data-pick-all=""> %s</label>' % esc(t("all"))]

    for state in sorted(counts, key=lambda s: (-counts[s], s)):
        toggles.append(
            '<label class="switch"><input type="checkbox" data-pick-all="%s"> %s'
            ' <span class="muted">(%d)</span></label>'
            % (attr(state), esc(t(STATE_PICK_LABELS.get(state, state))), counts[state]))

    return """<div class="picker" data-picker>
  %s
  <span class="muted" data-pick-count>%s</span>
  <span class="spacer"></span>
  <button data-pick-copy disabled>%s</button>
</div>""" % ("".join(toggles), esc(t("nothing selected")), esc(t("Copy links")))


def queue_body(payload):
    data = payload["main"]
    rows = []

    for item in data.get("queue") or []:
        marks = [chip(t(STATE_PICK_LABELS.get(item.get("state"), item.get("state") or "")),
                      STATE_TONES.get(item.get("state"), ""))]

        if item.get("open_threads"):
            marks.append(chip(count(item["open_threads"], "thread"), "wait"))

        if item.get("draft"):
            marks.append(chip(t("draft")))

        rows.append([
            _pick_box(item),
            link(item.get("web_url"), "!%s" % item.get("iid"), mono=True),
            '<span class="repo">%s</span>' % esc(item.get("project", "").split("/")[-1]),
            esc(item.get("version_name") or "—"),
            '<span class="repo">%s</span>' % esc(item.get("author")),
            '<span class="summary">%s</span>' % esc(item.get("title")),
            " ".join(marks),
        ])

    items = data.get("queue") or []
    queue = (_picker(items) + table(["", "MR", "Repo", "Release", "Author", "Title", "State"], rows)
             if rows else empty(t("The queue is empty — nothing to review.")))
    blocks = [section(t("Queue"), queue, chip(str(len(rows))))]

    skipped = data.get("skipped") or []

    if skipped:
        srows = [[link(s.get("web_url"), "!%s" % s.get("iid"), mono=True),
                  '<span class="repo">%s</span>' % esc(s.get("project", "").split("/")[-1]),
                  '<span class="summary">%s</span>' % esc(s.get("title")),
                  '<span class="muted">%s</span>' % esc(s.get("reason"))] for s in skipped]
        blocks.append(section(t("Skipped"), table(["MR", "Repo", "Title", "Reason"], srows),
                              chip(str(len(skipped)))))

    scanned = data.get("scanned") or {}

    if scanned:
        srows = [[esc(project), str(counts.get("open", 0)), str(counts.get("kolejka", 0)),
                  str(counts.get("moje", 0)), str(counts.get("pominiete", 0))]
                 for project, counts in scanned.items()]
        blocks.append(section(t("Repositories scanned"),
                              table(["Repo", "Open", "Queued", "Mine", "Skipped"], srows)))

    return "".join(blocks)


def queue_headline(payload):
    data = payload["main"]
    queue = data.get("queue") or []
    fresh = len([q for q in queue if q.get("state") == "nowy"])

    return " ".join([chip(t("%s queued") % count(len(queue), "MR")),
                     chip(t("%d new") % fresh, "accent" if fresh else "")])


def request_body(payload):
    data = payload["main"]
    mrs = data.get("merge_requests") or []
    blocks = []

    if payload.get("post"):
        blocks.append(section(
            t("The post"), '<pre class="raw">%s</pre>' % esc(payload["post"]),
            copy_button(t("Copy the post"), shown(payload["post"]))))

    rows = []

    for mr in mrs:
        marks = [chip(t("%d approve") % mr.get("approvals", 0), "ok" if mr.get("approvals") else "")]

        if mr.get("unresolved"):
            marks.append(chip(count(mr["unresolved"], "thread"), "wait"))

        rows.append([
            link(mr.get("url"), "!%s" % mr.get("iid"), mono=True),
            '<span class="repo">%s</span>' % esc(mr.get("project", "").split("/")[-1]),
            esc(mr.get("version_name") or "—"),
            '<span class="summary">%s</span>' % esc(mr.get("title")),
            chip(mr.get("jira_status") or "—"),
            " ".join(marks),
        ])

    blocks.append(section(t("My MRs short of approvals"),
                          table(["MR", "Repo", "Release", "Title", "Jira", "State"], rows)
                          or empty(t("Every MR of mine has a full set of approvals.")),
                          chip(str(len(rows)))))

    return "".join(blocks)


def request_headline(payload):
    mrs = payload["main"].get("merge_requests") or []
    none_yet = len([m for m in mrs if not m.get("approvals")])

    return " ".join([chip(t("%s waiting") % count(len(mrs), "MR")),
                     chip(t("%d with no approval") % none_yet, "wait" if none_yet else "")])
