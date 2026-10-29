"""The settings screen — the only place the hub writes its own configuration.

A stored secret is never rendered back. The field for one always comes up empty and the
form reports what is configured through a hint (`…3f0a`) and the source the skills will
actually read, so a value that exists can be recognised without being shown or copied out.
"""
from .. import config
from ..text import t

from .layout import chip, esc, section

SOURCE_LABELS = {"keychain": "Keychain", ".env": ".env", "environment": "the environment",
                 "file": "~/.claude/.secrets"}


def _state(item):
    """What is configured, and which source wins — they are not always the same thing."""
    if not item["source"]:
        return chip(t("not set"), "wait")

    label = t(SOURCE_LABELS.get(item["source"], item["source"]))
    parts = [chip(t("from %s") % label, "ok" if item["source"] != "keychain" else "")]

    if item["source"] == "keychain" and item["set"]:
        # auth.resolve_token reads the Keychain first, so a saved token would never be used.
        parts.append('<span class="muted">%s</span>' % esc(t("the Keychain outranks .env")))
    elif item["set"] and item["secret"]:
        parts.append('<span class="muted">%s</span>' % esc(item["hint"]))

    return " ".join(parts)


def _field(item):
    if item["secret"]:
        control = """<input type="password" class="setting-input" data-setting="%s"
         autocomplete="new-password" placeholder="%s">
  <label class="switch" title="%s">
    <input type="checkbox" data-setting-clear="%s"%s> %s
  </label>""" % (esc(item["key"]), esc(t("unchanged") if item["set"] else t("paste a token")),
                 esc(t("Remove the stored value from .env")),
                 esc(item["key"]), "" if item["set"] else " disabled", esc(t("clear")))
    else:
        control = '<input type="text" class="setting-input" data-setting="%s" value="%s" placeholder="%s">' % (
            esc(item["key"]), esc(item["hint"]), esc(t(item["placeholder"])))

    return """<div class="setting">
  <div class="setting-head">
    <label>%s</label>
    <span class="spacer"></span>
    %s
  </div>
  <div class="setting-control">%s</div>
  <p class="muted setting-note">%s%s</p>
</div>""" % (esc(t(item["label"])), _state(item), control, esc(t(item["note"])),
             esc(" " + t("Needs a restart of the hub.")) if item["restart"] else "")


def page_body():
    items = config.describe()
    blocks = ['<div class="banner info">%s</div>' % esc(t(
        "Settings go into the .env beside the repository — never into git. A saved token "
        "takes effect on the next panel refresh, and no token is ever shown back here."))]

    for group in config.GROUPS:
        fields = "".join(_field(i) for i in items if i["group"] == group)
        blocks.append(section(t(group), fields))

    blocks.append("""<div class="settings-actions">
  <label class="switch" title="%s">
    <input type="checkbox" data-settings-sync checked> %s
  </label>
  <span class="muted">%s</span>
  <span class="spacer"></span>
  <button class="primary" data-settings-save>%s</button>
</div>""" % (esc(t("Copy the tokens into files under ~/.claude/.secrets")),
             esc(t("also write to ~/.claude/.secrets")),
             esc(t("Required for worklog writing — tempo-fill reads the token only from a file.")),
             esc(t("Save"))))

    return '<div class="settings">%s</div>' % "".join(blocks)
