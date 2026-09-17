"""Panels about merge requests: the review queue and the review-request post."""
from collections import Counter

from ..text import count
from .layout import chip, copy_button, empty, esc, link, section, table

STATE_TONES = {"nowy": "accent", "re-review": "wait"}


# The queue's own vocabulary for how much attention an MR needs. The keys are the skill's
# own values and stay in its language; only what is shown is translated.
STATE_PICK_LABELS = {"nowy": "new", "re-review": "re-review"}


def _pick_box(item):
    return ('<input type="checkbox" class="pick" data-url="%s" data-state="%s"'
            ' aria-label="select MR !%s">'
            % (esc(item.get("web_url")), esc(item.get("state") or ""), esc(item.get("iid"))))


def _picker(items):
    """One toggle for everything, plus one per state so a whole kind can be picked at once."""
    counts = Counter(item.get("state") for item in items if item.get("state"))
    toggles = ['<label class="switch"><input type="checkbox" data-pick-all=""> all</label>']

    for state in sorted(counts, key=lambda s: (-counts[s], s)):
        toggles.append(
            '<label class="switch"><input type="checkbox" data-pick-all="%s"> %s'
            ' <span class="muted">(%d)</span></label>'
            % (esc(state), esc(STATE_PICK_LABELS.get(state, state)), counts[state]))

    return """<div class="picker" data-picker>
  %s
  <span class="muted" data-pick-count>nothing selected</span>
  <span class="spacer"></span>
  <button data-pick-copy disabled>Copy links</button>
</div>""" % "".join(toggles)


def queue_body(payload):
    data = payload["main"]
    rows = []

    for item in data.get("queue") or []:
        marks = [chip(item.get("state") or "", STATE_TONES.get(item.get("state"), ""))]

        if item.get("open_threads"):
            marks.append(chip(count(item["open_threads"], "thread"), "wait"))

        if item.get("draft"):
            marks.append(chip("draft"))

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
             if rows else empty("The queue is empty — nothing to review."))
    blocks = [section("Queue", queue, chip(str(len(rows))))]

    skipped = data.get("skipped") or []

    if skipped:
        srows = [[link(s.get("web_url"), "!%s" % s.get("iid"), mono=True),
                  '<span class="repo">%s</span>' % esc(s.get("project", "").split("/")[-1]),
                  '<span class="summary">%s</span>' % esc(s.get("title")),
                  '<span class="muted">%s</span>' % esc(s.get("reason"))] for s in skipped]
        blocks.append(section("Skipped", table(["MR", "Repo", "Title", "Reason"], srows),
                              chip(str(len(skipped)))))

    scanned = data.get("scanned") or {}

    if scanned:
        srows = [[esc(project), str(counts.get("open", 0)), str(counts.get("kolejka", 0)),
                  str(counts.get("moje", 0)), str(counts.get("pominiete", 0))]
                 for project, counts in scanned.items()]
        blocks.append(section("Repositories scanned",
                              table(["Repo", "Open", "Queued", "Mine", "Skipped"], srows)))

    return "".join(blocks)


def queue_headline(payload):
    data = payload["main"]
    queue = data.get("queue") or []
    fresh = len([q for q in queue if q.get("state") == "nowy"])

    return " ".join([chip("%s queued" % count(len(queue), "MR")),
                     chip("%d new" % fresh, "accent" if fresh else "")])


def request_body(payload):
    data = payload["main"]
    mrs = data.get("merge_requests") or []
    blocks = []

    if payload.get("post"):
        blocks.append(section(
            "The post", '<pre class="raw">%s</pre>' % esc(payload["post"]),
            copy_button("Copy the post", payload["post"])))

    rows = []

    for mr in mrs:
        marks = [chip("%d approve" % mr.get("approvals", 0), "ok" if mr.get("approvals") else "")]

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

    blocks.append(section("My MRs short of approvals",
                          table(["MR", "Repo", "Release", "Title", "Jira", "State"], rows)
                          or empty("Every MR of mine has a full set of approvals."),
                          chip(str(len(rows)))))

    return "".join(blocks)


def request_headline(payload):
    mrs = payload["main"].get("merge_requests") or []
    none_yet = len([m for m in mrs if not m.get("approvals")])

    return " ".join([chip("%s waiting" % count(len(mrs), "MR")),
                     chip("%d with no approval" % none_yet, "wait" if none_yet else "")])
