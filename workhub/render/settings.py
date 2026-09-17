"""The settings screen — the only place the hub writes its own configuration.

A stored secret is never rendered back. The field for one always comes up empty and the
form reports what is configured through a hint (`…3f0a`) and the source the skills will
actually read, so a value that exists can be recognised without being shown or copied out.
"""
from .. import config

from .layout import chip, esc, section

SOURCE_LABELS = {"keychain": "Keychain", ".env": ".env", "środowisko": "środowisko",
                 "plik": "~/.claude/.secrets"}


def _state(item):
    """What is configured, and which source wins — they are not always the same thing."""
    if not item["source"]:
        return chip("nieustawione", "wait")

    label = SOURCE_LABELS.get(item["source"], item["source"])
    parts = [chip("z %s" % label, "ok" if item["source"] != "keychain" else "")]

    if item["source"] == "keychain" and item["set"]:
        # auth.resolve_token reads the Keychain first, so a saved token would never be used.
        parts.append('<span class="muted">Keychain ma pierwszeństwo przed .env</span>')
    elif item["set"] and item["secret"]:
        parts.append('<span class="muted">%s</span>' % esc(item["hint"]))

    return " ".join(parts)


def _field(item):
    if item["secret"]:
        control = """<input type="password" class="setting-input" data-setting="%s"
         autocomplete="new-password" placeholder="%s">
  <label class="switch" title="Usuń zapisaną wartość z .env">
    <input type="checkbox" data-setting-clear="%s"%s> usuń
  </label>""" % (esc(item["key"]), "bez zmian" if item["set"] else "wklej token",
                 esc(item["key"]), "" if item["set"] else " disabled")
    else:
        control = '<input type="text" class="setting-input" data-setting="%s" value="%s" placeholder="%s">' % (
            esc(item["key"]), esc(item["hint"]), esc(item["placeholder"]))

    return """<div class="setting">
  <div class="setting-head">
    <label>%s</label>
    <span class="spacer"></span>
    %s
  </div>
  <div class="setting-control">%s</div>
  <p class="muted setting-note">%s%s</p>
</div>""" % (esc(item["label"]), _state(item), control, esc(item["note"]),
             " Wymaga restartu huba." if item["restart"] else "")


def page_body():
    items = config.describe()
    blocks = ['<div class="banner info">Ustawienia trafiają do pliku <code>.env</code> obok '
              'repozytorium — nigdy do gita. Zapisany token działa od następnego odświeżenia '
              'panelu; tokeny nie są nigdzie pokazywane z powrotem.</div>']

    for group in config.GROUPS:
        fields = "".join(_field(i) for i in items if i["group"] == group)
        blocks.append(section(group, fields))

    blocks.append("""<div class="settings-actions">
  <label class="switch" title="Skopiuj tokeny do plików w ~/.claude/.secrets">
    <input type="checkbox" data-settings-sync checked> zapisz też do ~/.claude/.secrets
  </label>
  <span class="muted">Wymagane przez zapis worklogów — tempo-fill czyta token tylko z pliku.</span>
  <span class="spacer"></span>
  <button class="primary" data-settings-save>Zapisz</button>
</div>""")

    return '<div class="settings">%s</div>' % "".join(blocks)
