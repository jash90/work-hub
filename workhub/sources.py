"""The panel registry — the only place that knows how a skill is invoked.

Navigation, the scheduler and the HTTP API all derive from PANELS, so adding a panel
means adding one entry here and one renderer.

A panel runs one or more commands; the payload is always {command name: parsed output},
so a renderer never has to care whether its panel happened to need one command or three.
"""
import datetime
import os

SKILLS = os.path.expanduser("~/.claude/skills")

MORNING = "poranek"
AFTERNOON = "popoludnie"
ON_DEMAND = "on_demand"

GROUP_LABELS = {
    MORNING: "Poranek (10:00)",
    AFTERNOON: "Po pracy (16:00)",
    ON_DEMAND: "Na żądanie",
}

JSON = "json"
TEXT = "text"


def skill(*parts):
    return os.path.join(SKILLS, *parts)


def current_month():
    return datetime.date.today().strftime("%m.%Y")


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
        "dashboard", "Moja praca", "Taski do zrobienia, MR-y gotowe do mergu, moje uwagi w cudzych MR-ach, rozjazd Jira ↔ GitLab.",
        (MORNING, AFTERNOON),
        [Command("main", [PY3, skill("my-work-dashboard", "scripts", "dashboard.py"), "--json"])],
    ),
    Panel(
        "releases", "Tablica release'owa", "Każde wydanie z moim taskiem, w pełnym składzie zespołu, ze stanem MR-ów.",
        (MORNING, AFTERNOON),
        [Command(
            "main", [PY3, skill("release-dashboard", "scripts", "release_dashboard.py"), "--json"],
            fallback=Command("main", [PY3, skill("release-dashboard", "scripts", "release_dashboard.py"),
                                      "--mine-only", "--json"]),
            fallback_note="Pełny skład zespołu niedostępny — Jira odrzuciła zapytanie o wersje (HTTP 400). "
                          "Pokazane są wyłącznie moje taski.")],
    ),
    Panel(
        "priority", "Priorytet wydania", "Moje nierozwiązane taski uszeregowane po dacie wydania.",
        (MORNING,),
        [Command("main", [PY3, skill("jira-release-priority", "release_priority.py"), "--json"])],
    ),
    Panel(
        "review-queue", "Kolejka review", "Cudze otwarte MR-y w kolejności wydań — od czego zacząć review.",
        (MORNING,),
        [Command("main", [PY3, skill("mr-review-queue", "scripts", "build_queue.py"), "--json"])],
    ),
    Panel(
        "pr-request", "Prośba o review", "Moje MR-y bez kompletu approve — gotowy post do wklejenia.",
        (MORNING,),
        [
            Command("main", [PY3, skill("pr-review-request", "make_post.py"), "--json"]),
            Command("post", [PY3, skill("pr-review-request", "make_post.py")], TEXT),
        ],
    ),
    Panel(
        "testing", "Moje w testach", "Co wypchnąłem do Internal testing i co z tego przeszło dalej.",
        (MORNING,),
        [Command("main", [PY3, skill("jira-my-testing-status", "check_status.py"), "--json"])],
    ),
    Panel(
        "commits", "Commity dnia", "Co dziś wpadło do repozytoriów i czy jest już na develop.",
        (AFTERNOON,),
        [
            Command("commits", [skill("daily-commit-summary", "gather-commits.sh"), "today"], TEXT),
            Command("merge", [skill("daily-commit-summary", "merge-status.sh"), "--no-fetch"], TEXT),
        ],
    ),
    Panel(
        "tempo", "Tempo", "Dni poniżej 8 h i propozycje worklogów wyliczone z commitów.",
        (AFTERNOON,),
        [
            Command("gaps", [PY3, skill("tempo-fill", "tempo.py"), "gaps"], TEXT),
            Command("propose", [PY3, skill("tempo-fill", "tempo.py"), "propose", "--json"]),
        ],
    ),
    Panel(
        "protokol", "Protokół odbioru", "Tickety bieżącego miesiąca z godzinami — podstawa protokołu.",
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
