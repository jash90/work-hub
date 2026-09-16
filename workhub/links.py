"""Jira key → its merge requests, joined from payloads the hub already holds.

Nothing new is fetched. The skills behind `releases`, `dashboard`, `review-queue` and
`pr-request` each match an MR to a ticket by the key in its title or branch
(`redge_work.gitlab.jira_key_of`), so the join is already done upstream — this module only
gathers those answers into one lookup the task-shaped panels can render.

A panel whose own payload carries MRs (dashboard tasks, the release board) keeps them;
this fills in the panels whose skill never reports one, `priority` and `testing`.
"""
import re

from . import store

# Richest first: whoever names an MR first wins the extra fields (approvals, threads).
SOURCES = ("releases", "dashboard", "review-queue", "pr-request")


def _mr(key, iid, url, repo=None, title=None, approvals=None, unresolved=None):
    if not (key and iid and url):
        return None

    return {"key": key, "iid": str(iid), "url": url, "repo": repo, "title": title,
            "approvals": approvals, "unresolved": unresolved}


def _from_releases(payload):
    for key, mrs in (payload.get("mrs") or {}).items():
        for mr in mrs:
            yield _mr(key, mr.get("iid"), mr.get("web_url"), mr.get("repo"), mr.get("title"),
                      mr.get("approval_count"), mr.get("unresolved"))


MR_URL = re.compile(r"/([^/]+)/-/merge_requests/(\d+)")


def _from_dashboard(payload):
    for mr in list(payload.get("ready") or []) + list(payload.get("other_mrs") or []):
        yield _mr(mr.get("key"), mr.get("iid"), mr.get("web_url"), mr.get("repo"),
                  mr.get("title"), mr.get("approval_count"), mr.get("unresolved"))

    for task in payload.get("tasks") or []:
        for mr in task.get("mrs") or []:
            yield _mr(task.get("key"), mr.get("iid"), mr.get("web_url"), mr.get("repo"))

    # Drift rows are the only place an already-merged MR surfaces, and a ticket sitting in
    # testing is exactly the one whose MR is no longer open.
    for row in payload.get("drift") or []:
        found = MR_URL.search(row.get("url") or "")

        if found:
            yield _mr(row.get("label"), found.group(2), row["url"], found.group(1),
                      row.get("detail"))


def _from_queue(payload):
    for item in payload.get("queue") or []:
        yield _mr(item.get("jira_key"), item.get("iid"), item.get("web_url"),
                  (item.get("project") or "").split("/")[-1], item.get("title"),
                  None, item.get("open_threads"))


def _from_request(payload):
    for mr in payload.get("merge_requests") or []:
        yield _mr(mr.get("jira_key"), mr.get("iid"), mr.get("url"),
                  (mr.get("project") or "").split("/")[-1], mr.get("title"),
                  mr.get("approvals"), mr.get("unresolved"))


READERS = {"releases": _from_releases, "dashboard": _from_dashboard,
           "review-queue": _from_queue, "pr-request": _from_request}


def build(read=None):
    """Returns {jira key: [mr, …]}, each MR once, from whatever panels have run."""
    read = read or (lambda panel_id: (store.read(panel_id) or {}).get("payload"))
    index = {}
    seen = set()

    for panel_id in SOURCES:
        payload = read(panel_id)

        if not isinstance(payload, dict):
            continue

        main = payload.get("main") if isinstance(payload.get("main"), dict) else payload

        for mr in READERS[panel_id](main):
            if not mr:
                continue

            identity = (mr["repo"], mr["iid"])

            if identity in seen:
                continue

            seen.add(identity)
            index.setdefault(mr["key"], []).append(mr)

    for mrs in index.values():
        mrs.sort(key=lambda m: m["iid"])

    return index


def merge(own, extra):
    """Panel's own MRs first, then anything the index knows that they did not list."""
    out = [dict(m, iid=str(m.get("iid")), url=m.get("web_url") or m.get("url")) for m in own or []]
    known = {(m.get("repo"), m["iid"]) for m in out}

    return out + [m for m in extra or [] if (m["repo"], m["iid"]) not in known]
