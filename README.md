# work-hub

A localhost web front-end over the ten Jira / GitLab / git / Tempo work skills in
`~/.claude/skills`. It answers the morning questions — what to start, what can be merged,
what to review, where Tempo is short — in a browser instead of a Claude Code session.

    http://localhost:8787

## How it works

The hub **never reimplements a skill**. Each panel runs that skill's own script with
`--json`, keeps the result in an envelope under `data/`, and renders it:

    skill script --json  →  data/<panel>.json  →  workhub/render/<module>.py  →  HTML

`workhub/sources.py` is the registry — the single place that knows how a skill is invoked.
Adding a panel means one entry there plus one renderer in `workhub/render/`.

Panels run **one at a time**. Four of them read the same `~/.claude/cache/mr-index.json`
(TTL 300 s), so running them in parallel would make each ask GitLab separately instead of
using the cache the first panel just filled.

### A failed refresh never blanks a panel

An envelope keeps the last good `payload` and the `fetched_at` that dates it. A failed run
only updates `attempted_at` and `error`, and the panel shows the older data under a banner.
The skills behind several panels exit hard when the VPN is down; yesterday's answer is
worth more than an empty page.

## Schedule

Two groups, run by a thread inside the server process:

| group | time | panels |
|---|---|---|
| poranek | 10:00 | dashboard, releases, priority, review-queue, pr-request, testing |
| po pracy | 16:00 | dashboard, releases, commits, tempo |
| na żądanie | — | protokol (monthly and expensive) |

It is **catch-up, not cron**: a group is due when its time has passed today and it has not
run today. A Mac asleep until 14:00 runs the morning group once on wake instead of losing
it — which is why the schedule lives here rather than in extra launchd agents. Weekdays only.

Override the times with `WORK_HUB_PORANEK=10:30` / `WORK_HUB_POPOLUDNIE=17:00`.

## Writing to Jira

Exactly one route changes anything outside this machine: `POST /api/tempo/log`, which runs
`tempo-fill`'s `tempo.py log <day> --yes`. It needs a click, a confirmation dialog and an
explicit `confirm: true` in the body. **No automatic job ever posts** — the 16:00 run only
computes proposals. Every attempt is appended to `data/write-log.jsonl`, and every guard
(weekend, holiday, day already logged, total ≠ 8 h) stays in the skill.

### The Tempo day editor

Each proposed day is editable before it is written. Hours move on the skill's own 15-minute
grid — `−`/`+` buttons, arrow keys, or typing — and the running total, the hint line and the
submit button update together. The day cannot be submitted until it is actually writable, so
a bad split is caught in the browser instead of coming back as the skill's `sys.exit`.

- entries can be removed, and a ticket can be added by key for work with no commit behind it;
- **niepełny dzień** is an explicit opt-in that passes `--allow-partial` for a day that is not 8 h;
- hour fields are text, not `type=number`: Chrome renders a number input in the page locale, so
  a Polish decimal comma typed by hand would read back as an empty value. `parseHours` accepts
  `1,75` and `1.75` alike, and flags anything else instead of silently treating it as zero;
- the decimal comma is rejected again server-side — the skill parses hours with `float()`.

Those rules live in `workhub/static/day-rules.js`, deliberately free of the DOM, and are
tested by running them under Node (`tests/test_day_rules.py`).

## Two panels need Claude

`commits` and `protokol` show what their scripts produce on their own and offer a
**„Skopiuj brief dla Claude"** button; the narrative (daily-commit-summary's `plain` field)
and the legal rewrite (protokół odbioru) still happen in a Claude Code session. The hub does
not pretend to have prose it has not got.

## Running it

launchd keeps it alive and starts it at login:

    launchctl load   ~/Library/LaunchAgents/work-hub.plist
    launchctl unload ~/Library/LaunchAgents/work-hub.plist
    launchctl kickstart -k gui/$UID/work-hub      # restart

Logs: `~/.work-hub.log` (starts), `~/.work-hub.err` (crashes). By hand: `bin/work-hub`.

The server binds **both loopback sockets** (`127.0.0.1` and `::1`) because `localhost`
resolves to `::1` first on this machine — an IPv4-only bind makes the browser show an error
page while `curl` works.

## Security

Single-user, loopback only, and it has a write path — so:

- binds only the loopback addresses, never `0.0.0.0`;
- refuses any request whose `Host` is not localhost (DNS rebinding);
- a CSRF token minted at start-up, required on every `POST`.

`http.server` is not a public web server and is not used as one.

## Look and feel

The visual layer is two files: **`workhub/static/app.css`** (tokens and components) and
**`workhub/render/layout.py`** (page shell, nav, badges, banners, tables).

The stylesheet is a port of the shadcn/ui design language into plain CSS — the same tokens
(`--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--border`, `--ring`,
`--radius`) expressed as HSL triplets, the same component anatomy (button variants, card,
badge, alert, table, input, tabs) and the same focus-visible ring. No React, no Tailwind, no
build step, so the hub keeps its zero-dependency start-up.

Navigation is a permanent left rail, grouped the way the overview is — poranek, po pracy,
na żądanie. Below 860px it slides away behind the header's hamburger and closes on Escape,
the scrim or a link, because a fixed rail would eat a phone screen; above it, it is simply
part of the layout. The header carries the current panel's name, the theme toggle and the
global refresh.

The theme follows the system and can be pinned to light or dark from the header; the choice
is stored per browser and applied before first paint so a dark page never flashes white.

## Tests

    /usr/bin/python3 -m unittest discover -s . -t . -p "test_*.py"

No network: the scheduler runs on an injected clock, the server tests bind an ephemeral
port, renderers run against inline payloads, and the Tempo write tests build the command
without ever running it. The day-rule tests shell out to Node and skip when it is absent.

## Dependencies

None. Standard library on `/usr/bin/python3` (3.9), plus `~/.claude/lib/redge_work` for
atomic cache writes and Polish plurals — the same library the skills use. `glab` must be on
PATH for `review-queue` and `protokol`.

## Known issue outside the hub

`release-dashboard --json` fails with **HTTP 400** from Jira on its team-roster query (the
`fixVersion in (…) AND assignee != currentUser()` phase) — a pre-existing bug in that skill,
reproducible straight from the terminal. The panel falls back to `--mine-only` and says so
in a banner, so it shows my own tasks rather than nothing.
