"""Polish text from the skills, shown in English when the interface is English.

The skills write in Polish: commit prose, review comments, drift advice, skip reasons, Tempo
descriptions. Their payloads are stored untouched — renderers still match on the skills' own
values — and the swap happens only at the moment a string is written into the page.

A string is translated once, by `claude -p`, and remembered in data/translations.json under
its own text. A string seen for the first time is shown as it is and queued; a panel refresh
translates its queue before the panel is reported finished, and anything a page render meets
on its own is translated in the background for the next load.
"""
import json
import os
import re
import subprocess
import threading

from redge_work import cache

from . import DATA_DIR
from .runner import PATH

CACHE = os.path.join(DATA_DIR, "translations.json")

POLISH_LETTERS = re.compile("[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
# Polish without a single diacritic still happens ("nowy", "draft bez MR"); these words do
# not occur in the English interface, so one of them is enough to call a string Polish.
POLISH_WORDS = re.compile(r"\b(nie|jest|bez|dla|przed|przez|oraz|lub|tylko|brak|jeszcze|"
                          r"czeka|nowy|nowe|zmiana|zmiany|poprawka|na|od|w|z)\b")

BATCH = 40
TIMEOUT = 300

PROMPT = """Translate each Polish string in the JSON array below into natural, concise English.
Keep unchanged: HTML tags such as <code>, ticket keys (ABC-123), merge request refs (!123),
file names, code identifiers, URLs, people's names and dates written as 28.10.
A string that is already English, or only a name, comes back as it is.
Reply with nothing but a JSON array of the same length and order.

"""

_lock = threading.Lock()
_pending = set()
_flushing = threading.Lock()
_cache = None


def looks_polish(text):
    """Prose only: a string without a space is a name, a key, a URL or a single code word."""
    return " " in text and bool(POLISH_LETTERS.search(text) or POLISH_WORDS.search(text))


def _known():
    global _cache

    if _cache is None:
        _cache = cache.read_json(CACHE, default=None) or {}

    return _cache


def english(text):
    """The English for `text` when one is known; otherwise `text`, queued for translation."""
    if not text or not looks_polish(text):
        return text

    with _lock:
        known = _known().get(text)

        if known is None:
            _pending.add(text)

    return known or text


def has_pending():
    with _lock:
        return bool(_pending)


def claude(texts):
    env = dict(os.environ, PATH=PATH)
    # Started from inside a Claude Code session the CLI would refuse to nest.
    env.pop("CLAUDECODE", None)
    proc = subprocess.run(
        ["claude", "-p", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
         "--no-session-persistence", "--output-format", "text", "--model", "haiku"],
        input=PROMPT + json.dumps(texts, ensure_ascii=False),
        capture_output=True, text=True, timeout=TIMEOUT, env=env)

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[-300:] or "claude exited with %d" % proc.returncode)

    out = proc.stdout

    return json.loads(out[out.index("["):out.rindex("]") + 1])


# Replaced in tests, so no test ever starts the model.
ask = claude


def flush(using=None):
    """Translate everything queued, including what pages queue meanwhile. Returns how many
    strings were added.

    A batch that fails stays out of the cache and out of the queue: it is asked again the
    next time a page or a refresh meets the same text, not in a tight loop.
    """
    added = {}

    with _flushing:
        while True:
            with _lock:
                texts = sorted(_pending - set(added))
                _pending.clear()

            if not texts:
                break

            _translate(texts, using or ask, added)

        if added:
            with _lock:
                _known().update(added)
                cache.write_json(CACHE, _known())

    return len(added)


def _translate(texts, model, added):
    """Fills `added`; a batch that fails or comes back the wrong length is skipped whole."""
    for start in range(0, len(texts), BATCH):
        batch = texts[start:start + BATCH]

        try:
            answer = model(batch)
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired):
            continue

        if len(answer) != len(batch):
            continue

        added.update((source, target) for source, target in zip(batch, answer)
                     if isinstance(target, str) and target.strip())


def flush_in_background():
    """For a page render: never make a reader wait for the model."""
    if has_pending() and not _flushing.locked():
        threading.Thread(target=flush, daemon=True).start()
