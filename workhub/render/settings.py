"""The settings screen — the only place the hub writes its own configuration.

A stored secret is never rendered back. The field for one always comes up empty and the
form reports what is configured through a hint (`…3f0a`) and the source the skills will
actually read, so a value that exists can be recognised without being shown or copied out.
"""
from .. import config

from .layout import chip, esc, section

SOURCE_LABELS = {"keychain": "Keychain", ".env": ".env", "environment": "the environment",
                 "file": "~/.claude/.secrets"}


def _state(item):
    """What is configured, and which source wins — they are not always the same thing."""
    if not item["source"]:
        return chip("not set", "wait")

    label = SOURCE_LABELS.get(item["source"], item["source"])
    parts = [chip("from %s" % label, "ok" if item["source"] != "keychain" else "")]

    if item["source"] == "keychain" and item["set"]:
        # auth.resolve_token reads the Keychain first, so a saved token would never be used.
        parts.append('<span class="muted">the Keychain outranks .env</span>')
    elif item["set"] and item["secret"]:
        parts.append('<span class="muted">%s</span>' % esc(item["hint"]))

    return " ".join(parts)


def _field(item):
    if item["secret"]:
        control = """<input type="password" class="setting-input" data-setting="%s"
         autocomplete="new-password" placeholder="%s">
  <label class="switch" title="Remove the stored value from .env">
    <input type="checkbox" data-setting-clear="%s"%s> clear
  </label>""" % (esc(item["key"]), "unchanged" if item["set"] else "paste a token",
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
             " Needs a restart of the hub." if item["restart"] else "")


def page_body():
    items = config.describe()
    blocks = ['<div class="banner info">Settings go into the <code>.env</code> beside the '
              'repository — never into git. A saved token takes effect on the next panel '
              'refresh, and no token is ever shown back here.</div>']

    for group in config.GROUPS:
        fields = "".join(_field(i) for i in items if i["group"] == group)
        blocks.append(section(group, fields))

    blocks.append("""<div class="settings-actions">
  <label class="switch" title="Copy the tokens into files under ~/.claude/.secrets">
    <input type="checkbox" data-settings-sync checked> also write to ~/.claude/.secrets
  </label>
  <span class="muted">Required for worklog writing — tempo-fill reads the token only from a file.</span>
  <span class="spacer"></span>
  <button class="primary" data-settings-save>Save</button>
</div>""")

    return '<div class="settings">%s</div>' % "".join(blocks)
