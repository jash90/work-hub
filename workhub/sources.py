"""The panel registry — the only place that knows how a skill is invoked.

Navigation, the scheduler and the HTTP API all derive from PANELS, so adding a panel
means adding one entry here and one renderer.

A panel runs one or more commands; the payload is always {command name: parsed output},
so a renderer never has to care whether its panel happened to need one command or three.
"""
import datetime
import os

SKILLS = os.path.expanduser("~/.claude/skills")

MORNING = "morning"
AFTERNOON = "afternoon"
ON_DEMAND = "on_demand"

GROUP_LABELS = {
    MORNING: "Morning (10:00)",
    AFTERNOON: "After work (16:00)",
    ON_DEMAND: "On demand",
}

JSON = "json"
TEXT = "text"


def skill(*parts):
    return os.path.join(SKILLS, *parts)


def current_month():
    return datetime.date.today().strftime("%m.%Y")


def month_weeks():
    """(Monday, Sunday) around the current month — whole weeks, so none renders half-empty."""
    today = datetime.date.today()
    first = today.replace(day=1)
    last = (first + datetime.timedelta(31)).replace(day=1) - datetime.timedelta(1)

    return (first - datetime.timedelta(first.weekday()),
            last + datetime.timedelta(6 - last.weekday()))


class Command:
    """One subprocess. `argv` may be a callable when an argument depends on today's date.

    `fallback` is a second Command tried when the first fails, for a skill that can still
    answer a narrower question — partial data with a note beats an empty panel.
    """

    def __init__(self, name, argv, parse=JSON, fallback=None, fallback_note=""):
        self.name = name
        self._argv = argv
        self.parse = parse
        self.fallback = fallback
        self.fallback_note = fallback_note

    def resolve(self):
        return list(self._argv() if callable(self._argv) else self._argv)


class Panel:
    def __init__(self, id, label, blurb, groups, commands, timeout=120):
        self.id = id
        self.label = label
        self.blurb = blurb
        self.groups = tuple(groups)
        self.commands = tuple(commands)
        self.timeout = timeout

    def scheduled_in(self, group):
        return group in self.groups


PY3 = "/usr/bin/python3"

PANELS = (
    # dashboard runs first on purpose: it fills the shared ~/.claude/cache/mr-index.json
    # that four other panels read, so they hit the cache instead of GitLab.
    Panel(
        "dashboard", "My work", "Tasks to start, merge requests ready to merge, my comments on other people's MRs, Jira ↔ GitLab drift.",
        (MORNING, AFTERNOON),
        [Command("main", [PY3, skill("my-work-dashboard", "scripts", "dashboard.py"), "--json"])],
    ),
    Panel(
        "releases", "Release board", "Every release carrying a task of mine, with the whole team and the state of their MRs.",
        (MORNING, AFTERNOON),
        [Command(
            "main", [PY3, skill("release-dashboard", "scripts", "release_dashboard.py"), "--json"],
            fallback=Command("main", [PY3, skill("release-dashboard", "scripts", "release_dashboard.py"),
                                      "--mine-only", "--json"]),
            fallback_note="The full team is unavailable — Jira refused the version query (HTTP 400). "
                          "Only my own tasks are shown.")],
    ),
    Panel(
        "priority", "Release priority", "My unresolved tasks ordered by release date.",
        (MORNING,),
        [Command("main", [PY3, skill("jira-release-priority", "release_priority.py"), "--json"])],
    ),
    Panel(
        "review-queue", "Review queue", "Other people's open MRs in release order — where to start reviewing.",
        (MORNING,),
        [Command("main", [PY3, skill("mr-review-queue", "scripts", "build_queue.py"), "--json"])],
    ),
    Panel(
        "pr-request", "Review request", "My MRs short of approvals — a post ready to paste.",
        (MORNING,),
        [
            Command("main", [PY3, skill("pr-review-request", "make_post.py"), "--json"]),
            Command("post", [PY3, skill("pr-review-request", "make_post.py")], TEXT),
        ],
    ),
    Panel(
        "testing", "Mine in testing", "What I pushed to Internal testing and what moved on from there.",
        (MORNING,),
        [Command("main", [PY3, skill("jira-my-testing-status", "check_status.py"), "--json"])],
    ),
    Panel(
        "commits", "Commits today", "What landed in the repositories today and whether it is on develop yet.",
        (AFTERNOON,),
        [
            Command("commits", [skill("daily-commit-summary", "gather-commits.sh"), "today"], TEXT),
            Command("merge", [skill("daily-commit-summary", "merge-status.sh"), "--no-fetch"], TEXT),
        ],
    ),
    Panel(
        "tempo", "Tempo", "Week by week: what Tempo already holds and what to add from commits.",
        (AFTERNOON,),
        [
            Command("gaps", [PY3, skill("tempo-fill", "tempo.py"), "gaps"], TEXT),
            Command("propose", [PY3, skill("tempo-fill", "tempo.py"), "propose", "--json"]),
            Command("worklogs", lambda: [PY3, skill("tempo-fill", "tempo.py"), "worklogs",
                                         "--from", month_weeks()[0].isoformat(),
                                         "--to", month_weeks()[1].isoformat(), "--json"]),
        ],
    ),
    Panel(
        "protokol", "Acceptance report", "This month's tickets with their hours — the basis of the report.",
        (ON_DEMAND,),
        [Command("main", lambda: [PY3, skill("protokol-odbioru", "gather.py"),
                                  "--month", current_month(), "--json"])],
        timeout=180,
    ),
)

BY_ID = {p.id: p for p in PANELS}


def group_panels(group):
    return [p for p in PANELS if p.scheduled_in(group)]


def grouped_panels():
    """Each panel once, under the earliest group that refreshes it — nav and overview."""
    seen = set()

    for group in (MORNING, AFTERNOON, ON_DEMAND):
        panels = [p for p in group_panels(group) if p.id not in seen]
        seen.update(p.id for p in panels)

        if panels:
            yield group, panels
