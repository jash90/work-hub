# work-hub

A localhost web front-end over the ten Jira / GitLab / git / Tempo work skills in
`~/.claude/skills`. It answers the morning questions — what to start, what can be merged,
what to review, where Tempo is short — in a browser instead of a Claude Code session.

    http://localhost:8787

> **This is not a standalone app.** It is the front-end half of a private toolchain: it runs
> scripts from `~/.claude/skills` and imports `~/.claude/lib/redge_work`, neither of which is
> published here. Without them a clone will not start — the import fails before a socket is
> bound. It is public as a worked example of a stdlib-only local dashboard, not as something
> to `git clone && run`. See **Dependencies**.

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

## Configuration

Everything machine-specific lives in a `.env` beside this file. It is in `.gitignore` and is
written `0600`; `.env.example` lists every key with no values behind it.

    cp .env.example .env      # then fill it in, or use the settings screen

**/settings** edits the same file from the browser. A stored secret is never rendered back —
a token field always comes up empty and the row reports what is configured through a hint
(`…3f0a`) plus the source the skills will actually read. Clearing one is explicit, because a
blank field has to mean "leave it alone" for a form that cannot show what it holds.

| key | what it does |
|---|---|
| `JIRA_TOKEN`, `GITLAB_TOKEN`, `CONFLUENCE_TOKEN` | PATs. Confluence has no consumer yet; Jira and Confluence need separate tokens. |
| `JIRA_BASE_URL` | builds `…/browse/KEY` links **in this UI only** — see below |
| `JIRA_PROJECT_KEYS` | comma-separated; the first is the placeholder in the Tempo day editor |
| `TEMPO_USER` | whose worklogs. Tempo has no token of its own — it uses the Jira PAT. |
| `WORK_HUB_PORT`, `WORK_HUB_MORNING`, `WORK_HUB_AFTERNOON` | read at start-up, so a change needs a restart |

Saved values are laid over `os.environ` in `runner._env()` — the one place every subprocess
gets its environment, so a token takes effect on the next panel run with no restart and the
hub never holds a secret in memory. `os.environ` itself is not touched.

**Two limits worth knowing before you go looking for a bug:**

- `JIRA_BASE_URL` decides where a ticket number points **on screen**. It does not decide which
  Jira the skills query — that host is hardcoded in `redge_work`, outside this repository.
- `redge_work.auth` resolves a token **Keychain → environment → file**, so a Keychain entry
  silently outranks anything saved here. The settings screen says so when it finds one.
- `tempo-fill` reads the Jira token *only* from `~/.claude/.secrets/jira-token` and never looks
  at the environment. The "also write to ~/.claude/.secrets" checkbox mirrors it there;
  without it, a token saved here works everywhere except writing worklogs.

## Schedule

Two groups, run by a thread inside the server process:

| group | time | panels |
|---|---|---|
| morning | 10:00 | dashboard, releases, priority, review-queue, pr-request, testing |
| after work | 16:00 | dashboard, releases, commits, tempo |
| on demand | — | protokol (monthly and expensive) |

It is **catch-up, not cron**: a group is due when its time has passed today and it has not
run today. A Mac asleep until 14:00 runs the morning group once on wake instead of losing
it — which is why the schedule lives here rather than in extra launchd agents. Weekdays only.

Override the times with `WORK_HUB_MORNING=10:30` / `WORK_HUB_AFTERNOON=17:00`.

## Writing to Jira

Three routes change anything outside this machine, all of them under `POST /api/tempo/`:
`log` (a day with nothing in Tempo yet), `replace` (make a day match a given split) and
`undo`. Each runs the matching `tempo-fill` subcommand with `--yes`, and each needs a click,
a confirmation dialog and an explicit `confirm: true` in the body. **No automatic job ever
posts** — the 16:00 run only computes proposals. Every attempt is appended to
`data/write-log.jsonl`, and every guard (weekend, holiday, the daily total, the 15-minute
grid, a worklog id that is not really there) stays in the skill.

`replace` is declarative: the entries it is given are the day's wanted end state, not a list
of operations. An entry prefixed with a worklog id is one Tempo already holds, an entry
without one is new, and a worklog the split does not mention is deleted. An empty split
therefore clears the day — which also works on worklogs this tool never wrote, unlike
`undo`, which can only take back what it recorded in `state/<day>.json`. That ledger is
rewritten from Tempo after every `replace`, or `undo` would later chase ids that are gone.

### The Tempo day editor

The month is walked one week at a time, and every workday in it is an editor: a day Tempo
already holds opens with its own worklogs, a day it holds nothing of opens with the proposal
derived from commits. **One day, one editor** — two cards for the same day would mean two
truths about it, and the stale one would be the easier to submit. Weekends and holidays are
shown but not editable; the skill refuses to write them anyway.

Hours move on the skill's own 15-minute grid — `−`/`+` buttons, arrow keys, or typing — and
the running total, the hint line and the submit button update together. The day cannot be
submitted until it is actually writable, so a bad split is caught in the browser instead of
coming back as the skill's `sys.exit`.

- entries can be removed, and a ticket can be added by key for work with no commit behind it;
- **short day** and **overtime** are separate opt-ins, passing `--allow-partial` and
  `--allow-overtime`. They are separate because the skill treats the two directions
  separately: neither flag quietly excuses the other;
- a written day is greyed out until the panel refresh lands. Its worklog ids are a moment
  old, so a second submit would post the new rows again rather than edit them;
- hour fields are text, not `type=number`: Chrome renders a number input in the page locale, so
  a decimal comma typed by hand would read back as an empty value. `parseHours` accepts
  `1,75` and `1.75` alike, and flags anything else instead of silently treating it as zero;
- the decimal comma is rejected again server-side — the skill parses hours with `float()`.

Those rules live in `workhub/static/day-rules.js`, deliberately free of the DOM, and are
tested by running them under Node (`tests/test_day_rules.py`).

## Two panels need Claude

`commits` and `protokol` show what their scripts produce on their own and offer a
**“Copy the brief for Claude”** button; the narrative (daily-commit-summary's `plain` field)
and the legal rewrite (the acceptance report) still happen in a Claude Code session. The hub
does not pretend to have prose it has not got.

## Running it

launchd keeps it alive and starts it at login:

    launchctl load   ~/Library/LaunchAgents/work-hub.plist
    launchctl unload ~/Library/LaunchAgents/work-hub.plist
    launchctl kickstart -k gui/$UID/work-hub                # restart

Logs: `~/.work-hub.log` (starts), `~/.work-hub.err` (crashes). By hand: `bin/work-hub`.

The server binds **both loopback sockets** (`127.0.0.1` and `::1`) because `localhost`
resolves to `::1` first on this machine — an IPv4-only bind makes the browser show an error
page while `curl` works.

## Security

Single-user, loopback only, and it has a write path — so:

- binds only the loopback addresses, never `0.0.0.0`;
- refuses any request whose `Host` is not localhost (DNS rebinding);
- a CSRF token minted at start-up, required on every `POST`;
- `.env` is `0600` and git-ignored, and no route ever returns a stored secret — `/api/settings`
  reports a four-character tail and which source wins, nothing more.

`http.server` is not a public web server and is not used as one.

## Look and feel

The visual layer is two files: **`workhub/static/app.css`** (tokens and components) and
**`workhub/render/layout.py`** (page shell, nav, badges, banners, tables).

The stylesheet is a port of the shadcn/ui design language into plain CSS — the same tokens
(`--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--border`, `--ring`,
`--radius`) expressed as HSL triplets, the same component anatomy (button variants, card,
badge, alert, table, input, tabs) and the same focus-visible ring. No React, no Tailwind, no
build step, so the hub keeps its zero-dependency start-up.

Navigation is a permanent left rail, grouped the way the overview is — morning, after work,
on demand. Below 860px it slides away behind the header's hamburger and closes on Escape,
the scrim or a link, because a fixed rail would eat a phone screen; above it, it is simply
part of the layout. The header carries the current panel's name, the theme toggle and the
global refresh.

### Picking merge requests out of the queue

Rows in the review queue carry a checkbox. Pick several, hit **Skopiuj linki** and their
URLs land in the clipboard, one per line. Beside the **wszystkie** toggle there is one per
queue state — **nowe** and **re-review**, each with its count — so a whole kind can be taken
in one click; every toggle goes indeterminate when only part of its rows are picked, and the
counter says how many of how many. Selection is per-page state; nothing is stored and
nothing is sent.

The state toggles are generated from the states actually present in the payload, so a new
one coming out of `mr-review-queue` appears on its own.

Clipboard access can be refused even on localhost, so the copy falls back to a hidden
textarea and `execCommand` rather than failing silently.

### Ticket → merge request

Every ticket number on a task-shaped panel carries a clickable `!706` chip pointing at the
merge request that mentions it. Nothing extra is fetched: the skills behind `releases`,
`dashboard`, `review-queue` and `pr-request` each already match an MR to a ticket by the key
in its title or branch (`redge_work.gitlab.jira_key_of`), so `workhub/links.py` only gathers
those answers from the stored payloads into one `key → MRs` lookup.

`priority` and `testing` gain the column outright — their own skills never report an MR.
`dashboard` keeps the MRs its payload lists and picks up anyone else's on the same ticket.
The chip is amber when threads are unresolved, green at two approvals, and its tooltip
carries the repo, the MR title and the counts.

**What it cannot show:** merge requests that are already merged. The lookup only sees what
those four panels hold, which is the open MRs across the configured groups, plus whatever a drift
row still names. A ticket in Internal testing will usually show no MR for that reason —
covering merged history would mean a new GitLab query rather than a join over what is here.

The theme follows the system and can be pinned to light or dark from the header; the choice
is stored per browser and applied before first paint so a dark page never flashes white.

## Tests

    /usr/bin/python3 -m unittest discover -s . -t . -p "test_*.py"

No network: the scheduler runs on an injected clock, the server tests bind an ephemeral
port, renderers run against inline payloads, and the Tempo write tests build the command
without ever running it. The day-rule tests shell out to Node and skip when it is absent.

## Dependencies

No third-party packages: standard library on `/usr/bin/python3` (3.9).

It is **not self-contained**, though. `~/.claude/lib/redge_work` (atomic cache writes and
the token resolver) is imported at load time, and the panels shell
out to nine scripts under `~/.claude/skills`. Neither is published here, so a clone of this
repository alone will raise `ImportError` before the server starts. `glab` must also be on
PATH for `review-queue` and `protokol`.

