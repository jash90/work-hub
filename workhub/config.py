"""Settings: the `.env` beside this file, and the table describing what may live in it.

The hub owns no credential. It runs the skills as subprocesses, and they resolve their own
tokens — Keychain first, then an environment variable, then a file under ~/.claude/.secrets
(see redge_work.auth). All this module does is put the values from `.env` into the
environment those subprocesses inherit, which is why saving one takes effect on the next
panel run rather than needing a restart.

SETTINGS is the single source of truth: the form, `.env.example` and the POST validation
are all generated from it, so a new key is one row here rather than four edits.
"""
import os

from . import ROOT

ENV_PATH = os.environ.get("WORK_HUB_ENV") or os.path.join(ROOT, ".env")
SECRETS_DIR = os.environ.get("WORK_HUB_SECRETS_DIR") or os.path.expanduser("~/.claude/.secrets")
HINT_TAIL = 4


class Setting:
    def __init__(self, key, label, group, note, secret=False, placeholder="", restart=False):
        self.key = key
        self.label = label
        self.group = group
        self.note = note
        self.secret = secret
        self.placeholder = placeholder
        # Read once at start-up by the server or the scheduler, so a save is not enough.
        self.restart = restart


TOKENS = "Tokeny"
JIRA = "Jira i GitLab"
HUB = "Hub"

SETTINGS = (
    Setting("JIRA_TOKEN", "Jira — Personal Access Token", TOKENS, secret=True,
            note="Używany przez większość paneli. Zapis worklogów czyta go wyłącznie z pliku "
                 "w ~/.claude/.secrets — zaznacz synchronizację poniżej, inaczej Tempo go nie zobaczy."),
    Setting("GITLAB_TOKEN", "GitLab — Personal Access Token", TOKENS, secret=True,
            note="Kolejka review, pr-request i wspólny indeks merge requestów."),
    Setting("CONFLUENCE_TOKEN", "Confluence — Personal Access Token", TOKENS, secret=True,
            note="Żaden panel jeszcze go nie używa; przechowywany dla skilli sięgających po Confluence. "
                 "Jira i Confluence wymagają osobnych tokenów."),
    Setting("JIRA_BASE_URL", "Adres Jiry", JIRA, placeholder="https://jira.example.com",
            note="Buduje linki „…/browse/KEY” w interfejsie. Nie zmienia tego, do której Jiry pytają "
                 "skille — ten adres jest zaszyty w redge_work poza tym repozytorium."),
    Setting("JIRA_PROJECT_KEYS", "Klucze projektów", JIRA, placeholder="ABC, DEF",
            note="Po przecinku. Pierwszy z nich jest podpowiedzią w edytorze dnia Tempo."),
    Setting("TEMPO_USER", "Nazwa użytkownika w Tempo", JIRA, placeholder="imie.nazwisko",
            note="Właściciel worklogów. Tempo nie ma osobnego tokenu — korzysta z PAT-a Jiry."),
    Setting("WORK_HUB_PORT", "Port", HUB, placeholder="8787", restart=True,
            note="Serwer słucha wyłącznie na pętli zwrotnej."),
    Setting("WORK_HUB_PORANEK", "Przebieg poranny", HUB, placeholder="10:00", restart=True,
            note="Godzina HH:MM."),
    Setting("WORK_HUB_POPOLUDNIE", "Przebieg popołudniowy", HUB, placeholder="16:00", restart=True,
            note="Godzina HH:MM."),
)

BY_KEY = {s.key: s for s in SETTINGS}
GROUPS = (TOKENS, JIRA, HUB)

# Where a token lands for the skills that read a file rather than the environment.
SECRET_FILES = {"JIRA_TOKEN": "jira-token", "GITLAB_TOKEN": "gitlab-token",
                "CONFLUENCE_TOKEN": "confluence-token"}

DEFAULTS = {"JIRA_BASE_URL": "", "JIRA_PROJECT_KEYS": ""}


_cache = {"stamp": None, "values": {}}


def load():
    """Parse `.env`. A malformed line is skipped rather than taking the whole hub down.

    Re-read only when the file changes: every ticket link on a page asks for the base URL,
    and a long table should not mean a hundred opens of the same four lines.
    """
    try:
        info = os.stat(ENV_PATH)
        stamp = (info.st_mtime_ns, info.st_size)
    except OSError:
        _cache.update(stamp=None, values={})

        return {}

    if _cache["stamp"] == stamp:
        return _cache["values"]

    values = {}

    try:
        with open(ENV_PATH, encoding="utf-8") as handle:
            lines = handle.readlines()
    except (IOError, UnicodeDecodeError):
        return values

    for line in lines:
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        value = value.strip()

        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]

        if value:
            values[key.strip()] = value

    _cache.update(stamp=stamp, values=values)

    return values


def get(key, default=""):
    """One setting, `.env` first so a saved value beats whatever launchd exported."""
    return load().get(key) or os.environ.get(key) or DEFAULTS.get(key, default)


def jira_base_url():
    return get("JIRA_BASE_URL").rstrip("/")


def project_keys():
    return [k.strip().upper() for k in get("JIRA_PROJECT_KEYS").split(",") if k.strip()]


def save(values):
    """Merge `values` into `.env`. A key that is absent keeps its value, an empty one drops it.

    Absent and empty have to mean different things: the form cannot show a stored token, so
    it sends none unless one was typed, and rewriting from the form alone would wipe every
    secret on each save. Clearing is therefore explicit — an empty string, never a silence.
    """
    unknown = sorted(k for k in values if k not in BY_KEY)

    if unknown:
        raise KeyError(unknown[0])

    merged = dict(load())
    merged.update({k: str(v).strip() for k, v in values.items()})
    kept = {k: v for k, v in merged.items() if v and k in BY_KEY}
    body = "".join("%s=%s\n" % (s.key, kept[s.key]) for s in SETTINGS if s.key in kept)
    tmp = ENV_PATH + ".tmp"

    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write("# work-hub — lokalna konfiguracja. Nigdy nie trafia do gita.\n" + body)

    os.chmod(tmp, 0o600)
    os.replace(tmp, ENV_PATH)
    _cache.update(stamp=None, values={})

    return kept


def sync_secret_files(values):
    """Mirror tokens into ~/.claude/.secrets for the skills that only read a file.

    tempo-fill is the one that matters: it opens the file directly and never looks at the
    environment, so without this a token saved here could log in everywhere but Tempo.
    """
    written = []

    for key, name in SECRET_FILES.items():
        token = str(values.get(key) or "").strip()

        if not token:
            continue

        os.makedirs(SECRETS_DIR, exist_ok=True)
        path = os.path.join(SECRETS_DIR, name)
        tmp = path + ".tmp"

        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")

        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        written.append(name)

    return written


def _keychain_has(key):
    """Keychain wins over the environment in redge_work.auth, so it can shadow a saved token."""
    service = {"JIRA_TOKEN": "claude-jira-token", "GITLAB_TOKEN": "claude-gitlab-token"}.get(key)

    if not service:
        return False

    try:
        from redge_work import auth
    except ImportError:
        return False

    return bool(auth.from_keychain(service))


def _source(key, saved):
    """Which source the skills will actually read — not merely where a value exists."""
    if _keychain_has(key):
        return "keychain"

    if saved.get(key):
        return ".env"

    if os.environ.get(key):
        return "środowisko"

    name = SECRET_FILES.get(key)

    if name and os.path.exists(os.path.join(SECRETS_DIR, name)):
        return "plik"

    return ""


def _hint(setting, value):
    """A secret is described, never echoed: four trailing characters and nothing more."""
    if not value:
        return ""

    if not setting.secret:
        return value

    return "…" + value[-HINT_TAIL:] if len(value) > HINT_TAIL else "…"


def describe():
    """What the settings view renders. A secret's value never appears in the result."""
    saved = load()
    out = []

    for setting in SETTINGS:
        value = saved.get(setting.key, "")
        out.append({
            "key": setting.key,
            "label": setting.label,
            "group": setting.group,
            "note": setting.note,
            "secret": setting.secret,
            "placeholder": setting.placeholder,
            "restart": setting.restart,
            "set": bool(value),
            "hint": _hint(setting, value),
            "source": _source(setting.key, saved),
        })

    return out


def example():
    """`.env.example` — every key, no values, so the real file is never the template."""
    lines = ["# work-hub — skopiuj do .env i uzupełnij. .env jest w .gitignore.", ""]

    for group in GROUPS:
        lines.append("# --- %s ---" % group)

        for setting in SETTINGS:
            if setting.group == group:
                lines.append("# %s" % setting.label)
                lines.append("%s=%s" % (setting.key, setting.placeholder))

        lines.append("")

    return "\n".join(lines)
