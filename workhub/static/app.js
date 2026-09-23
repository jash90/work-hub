// Refresh buttons, theme, clipboard briefs and the Tempo day editor.
// Every POST carries the start-up CSRF token the page holds in <html data-csrf>.
const CSRF = document.documentElement.dataset.csrf;
// Both come from the hub's own settings; without an address a ticket number stays plain text.
const JIRA = document.documentElement.dataset.jira || '';
const KEY_HINT = (document.documentElement.dataset.keys || '').split(',')[0] || 'ABC';

function ticketLink(key) {
  return JIRA
    ? `<a class="key" href="${JIRA}/browse/${key}" target="_blank" rel="noopener">${key}</a>`
    : `<span class="key">${key}</span>`;
}

/* ---------- theme ---------- */

const THEMES = ['auto', 'light', 'dark'];
const THEME_GLYPH = { auto: '◐', light: '☀', dark: '☾' };
const THEME_TITLE = { auto: 'Theme: automatic', light: 'Theme: light', dark: 'Theme: dark' };

function readTheme() {
  try {
    return localStorage.getItem('work-hub-theme') || 'auto';
  } catch (e) {
    return 'auto';
  }
}

function applyTheme(theme) {
  if (theme === 'auto') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;

  try {
    localStorage.setItem('work-hub-theme', theme);
  } catch (e) { /* private window — the theme just won't stick */ }

  for (const button of document.querySelectorAll('[data-theme-toggle]')) {
    button.textContent = THEME_GLYPH[theme];
    button.title = THEME_TITLE[theme];
  }
}

/* ---------- toasts ---------- */

function toast(text, tone = '', ms = 4000) {
  const stack = document.querySelector('.toast-stack');

  if (!stack) return;

  const node = document.createElement('div');
  node.className = 'toast';
  if (tone) node.dataset.tone = tone;
  node.textContent = text;
  stack.appendChild(node);
  setTimeout(() => node.remove(), ms);
}

/* ---------- transport ---------- */

async function post(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF': CSRF },
    body: JSON.stringify(body),
  });

  return { status: response.status, data: await response.json().catch(() => ({})) };
}

const state = async () => (await fetch('/api/state')).json();

/* ---------- refreshing ---------- */

function busy(ids, on) {
  for (const id of ids) {
    for (const button of document.querySelectorAll(`[data-refresh="${id}"]`)) {
      button.disabled = on;
      button.setAttribute('aria-busy', String(on));
      button.textContent = on ? 'Refreshing' : 'Refresh';
    }
  }
}

async function repaint(panel) {
  const host = document.querySelector(`[data-panel="${panel.id}"] [data-fragment]`);

  if (host) {
    host.innerHTML = await (await fetch(`/p/${panel.id}/fragment`)).text();
    bind(host);
  }
}

// Poll until the named panels stop running, then bring their markup up to date.
async function follow(ids) {
  const pending = new Set(ids);
  let refreshedCards = false;

  while (pending.size) {
    await new Promise((resolve) => setTimeout(resolve, 900));
    const now = await state();

    for (const panel of now.panels) {
      if (!pending.has(panel.id) || panel.running) continue;

      pending.delete(panel.id);
      busy([panel.id], false);
      await repaint(panel);

      if (panel.error && panel.fetched_at) toast(`${panel.label}: showing older data, the refresh failed`, 'bad', 7000);
      else if (panel.error) toast(`${panel.label}: ${panel.error.slice(0, 160)}`, 'bad', 8000);

      if (document.querySelector('.grid')) refreshedCards = true;
    }

    paintOvertime(now.overtime);
  }

  if (refreshedCards) return window.location.reload();

  document.querySelector('[data-refresh-all]')?.removeAttribute('aria-busy');
}

document.addEventListener('click', async (event) => {
  if (event.target.closest('[data-nav-open]')) return setNav(true);
  if (event.target.closest('[data-nav-close]')) return setNav(false);

  const theme = event.target.closest('[data-theme-toggle]');

  if (theme) {
    applyTheme(THEMES[(THEMES.indexOf(readTheme()) + 1) % THEMES.length]);

    return;
  }

  const one = event.target.closest('[data-refresh]');
  const all = event.target.closest('[data-refresh-all]');

  if (!one && !all) return;

  const { data } = await post('/api/refresh', all ? { all: true } : { panel: one.dataset.refresh });
  const ids = data.started || [];

  busy(ids, true);
  if (all) event.target.closest('[data-refresh-all]').setAttribute('aria-busy', 'true');
  toast(all ? 'Refreshing every panel…' : 'Refreshing…');
  await follow(ids);
});

/* ---------- clipboard ---------- */

function bindCopy(root) {
  for (const button of root.querySelectorAll('[data-copy]')) {
    button.onclick = async () => {
      const text = new TextDecoder().decode(
        Uint8Array.from(atob(button.dataset.copy), (c) => c.charCodeAt(0)),
      );

      const ok = await toClipboard(text);
      toast(ok ? 'Copied to the clipboard' : 'The browser refused access to the clipboard',
            ok ? 'ok' : 'bad');
    };
  }
}

/* ---------- tempo day editor ---------- */

// QUARTER, round15, fmt, parseHours and dayVerdict come from day-rules.js.
const readHours = (input) => parseHours(input.value);

function dayEntries(day) {
  return [...day.querySelectorAll('[data-entry]')].map((row) => ({
    row,
    key: row.querySelector('.entry-key a, .entry-key').textContent.trim(),
    // A row that came out of Tempo carries its worklog id, so an edit lands on that entry
    // instead of adding a second one beside it.
    id: row.dataset.worklogId || '',
    hours: readHours(row.querySelector('.hours')),
  }));
}

function refreshDay(day) {
  const all = dayEntries(day);
  const target = Number(day.dataset.target);
  const partial = day.querySelector('[data-partial]').checked;
  const overtime = day.querySelector('[data-overtime]').checked;
  const verdict = dayVerdict(all.map((e) => e.hours), target, partial, overtime);

  for (const entry of all) {
    entry.row.querySelector('.hours').setAttribute('aria-invalid', String(Number.isNaN(entry.hours)));
  }

  const badge = day.querySelector('[data-total]');
  badge.textContent = `${fmt(verdict.total)} h`;
  badge.className = `chip ${verdict.total === target ? 'ok' : 'wait'}`;

  const hint = day.querySelector('[data-hint]');
  hint.textContent = verdict.note;
  hint.dataset.tone = verdict.ok ? 'ok' : 'bad';

  day.dataset.valid = verdict.ok ? 'yes' : 'no';
  const submit = day.querySelector('[data-tempo-log]');
  submit.disabled = !verdict.ok;
  submit.title = verdict.problem || 'Writes the worklogs to Tempo';

  return { entries: all.filter((e) => e.hours > 0), total: verdict.total, partial, overtime };
}

// A written day still shows what was on screen a moment ago: the ids it holds are stale and
// a second submit would post the new rows again. The panel refresh runs in the background,
// so the card is closed until it arrives rather than left looking editable.
function markStale(day, note) {
  day.dataset.stale = 'yes';

  for (const field of day.querySelectorAll('input, button')) field.disabled = true;

  const hint = day.querySelector('[data-hint]');
  hint.textContent = note;
  hint.dataset.tone = 'ok';
}

function entriesString(entries) {
  return entries.map((e) => `${e.id ? `${e.id}:` : ''}${e.key}=${fmt(e.hours)}`).join(',');
}

function addEntryRow(day, key, hours) {
  const body = day.querySelector('.entries-table tbody');
  const row = document.createElement('tr');
  row.className = 'entry';
  row.dataset.entry = '';
  row.innerHTML = `
    <td class="entry-key">${ticketLink(key)}</td>
    <td class="entry-summary"><span class="muted">added by hand</span></td>
    <td class="entry-commits"></td>
    <td class="entry-hours">
      <div class="stepper">
        <button type="button" class="step" data-step="-0.25" aria-label="15 minutes less">−</button>
        <input type="text" class="hours" value="${fmt(hours)}" inputmode="decimal" autocomplete="off">
        <button type="button" class="step" data-step="0.25" aria-label="15 minutes more">+</button>
      </div>
    </td>
    <td class="entry-drop"><button type="button" class="ghost" data-drop aria-label="remove entry">×</button></td>`;
  body.appendChild(row);
}

function bindTempo(root) {
  // Only the editors: a weekend card is a `.day` too, and it carries no switches to read.
  for (const day of root.querySelectorAll('.day[data-day]')) {
    const update = () => refreshDay(day);

    day.addEventListener('input', (event) => {
      if (event.target.classList.contains('hours')) update();
    });

    day.addEventListener('change', (event) => {
      if (event.target.matches('[data-partial], [data-overtime]')) update();

      if (event.target.classList.contains('hours')) {
        const hours = readHours(event.target);

        if (!Number.isNaN(hours)) event.target.value = fmt(round15(hours));

        update();
      }
    });

    // Text fields lose the native spinner, so keep arrow keys stepping by 15 minutes.
    day.addEventListener('keydown', (event) => {
      if (!event.target.classList.contains('hours')) return;

      const direction = { ArrowUp: 1, ArrowDown: -1 }[event.key];

      if (!direction) return;

      event.preventDefault();
      const hours = readHours(event.target);
      event.target.value = fmt(round15((Number.isNaN(hours) ? 0 : hours) + direction * QUARTER));
      update();
    });

    day.addEventListener('click', async (event) => {
      const step = event.target.closest('.step');
      const drop = event.target.closest('[data-drop]');
      const add = event.target.closest('[data-add]');

      if (step) {
        const input = step.parentElement.querySelector('.hours');
        const hours = readHours(input);
        input.value = fmt(round15((Number.isNaN(hours) ? 0 : hours) + Number(step.dataset.step)));
        update();

        return;
      }

      if (drop) {
        drop.closest('tr').remove();
        update();

        return;
      }

      if (add) {
        const keyField = day.querySelector('.add-key');
        const key = keyField.value.trim().toUpperCase();

        if (!/^[A-Z][A-Z0-9]*-\d+$/.test(key)) {
          keyField.setAttribute('aria-invalid', 'true');
          toast(`A ticket key looks like ${KEY_HINT}-1234`, 'bad');

          return;
        }

        keyField.removeAttribute('aria-invalid');
        const addHours = readHours(day.querySelector('.add-hours'));
        addEntryRow(day, key, round15(Number.isNaN(addHours) || !addHours ? QUARTER : addHours));
        keyField.value = '';
        update();

        return;
      }

      const log = event.target.closest('[data-tempo-log]');
      const undo = event.target.closest('[data-tempo-undo]');
      const clear = event.target.closest('[data-tempo-clear]');

      if (log) await submitDay(day, log);
      if (undo) await undoDay(day, undo);
      if (clear) await clearDay(day, clear);
    });

    update();
  }
}

async function write(day, button, body, done) {
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');

  const { data } = await post(body.endpoint, { ...body.payload, day: day.dataset.day, confirm: true });

  button.removeAttribute('aria-busy');
  button.disabled = false;

  if (data.ok) markStale(day, done);

  toast(data.ok ? done : `Refused: ${(data.output || data.error || '').slice(0, 200)}`,
        data.ok ? 'ok' : 'bad', data.ok ? 4000 : 9000);
}

async function submitDay(day, button) {
  const { entries, total, partial, overtime } = refreshDay(day);

  if (day.dataset.valid !== 'yes' || day.dataset.stale) return;

  const target = Number(day.dataset.target);
  const listing = entries.map((e) => `  ${e.key} — ${fmt(e.hours)} h`).join('\n');
  let label = '';

  if (total < target) label = ' (short day)';
  else if (total > target) label = ' (overtime)';

  if (!confirm(`Write worklogs to Tempo for ${day.dataset.day}${label}?\n\n${listing}\n\n${fmt(total)} h in total. This is a real POST to Jira.`)) return;

  await write(day, button, {
    endpoint: day.dataset.endpoint,
    payload: { entries: entriesString(entries), allow_partial: partial, allow_overtime: overtime },
  }, `Saved ${day.dataset.day} — ${fmt(total)} h`);
}

// Clearing goes through the same declarative route as an edit: an empty split is a day with
// nothing in it, so it works on worklogs this tool never wrote.
async function clearDay(day, button) {
  if (day.dataset.stale) return;

  if (!confirm(`Clear ${day.dataset.day} in Tempo? This deletes every worklog on that day.`)) return;

  await write(day, button, { endpoint: '/api/tempo/replace', payload: { entries: '' } },
              `Cleared ${day.dataset.day}`);
}

async function undoDay(day, button) {
  if (day.dataset.stale) return;

  if (!confirm(`Undo the worklogs for ${day.dataset.day}? They will be deleted from Jira.`)) return;

  await write(day, button, { endpoint: '/api/tempo/undo', payload: {} }, `Undone ${day.dataset.day}`);
}

function bindWeeks(root) {
  for (const weeks of root.querySelectorAll('[data-weeks]')) {
    const sections = [...weeks.querySelectorAll('.week')];
    const label = weeks.querySelector('[data-week-label]');
    const total = weeks.querySelector('[data-week-total]');
    const steps = [...weeks.querySelectorAll('[data-week-step]')];

    const show = (index) => {
      const active = Math.min(Math.max(index, 0), sections.length - 1);
      weeks.dataset.active = String(active);

      for (const [at, week] of sections.entries()) week.hidden = at !== active;

      label.textContent = sections[active].dataset.label;
      total.textContent = sections[active].dataset.total;

      for (const step of steps) {
        const to = active + Number(step.dataset.weekStep);
        step.disabled = to < 0 || to > sections.length - 1;
      }
    };

    for (const step of steps) {
      step.onclick = () => show(Number(weeks.dataset.active) + Number(step.dataset.weekStep));
    }

    show(Number(weeks.dataset.active));
  }
}

/* ---------- release board: folding ---------- */

// A release finished for me starts folded, but an explicit choice outranks that rule in both
// directions and survives a reload. Only explicit choices are stored, so a release that later
// finishes still folds itself, and one that reopens still unfolds.
const FOLD_KEY = 'work-hub-folded-releases';

function readFolds() {
  try {
    return JSON.parse(localStorage.getItem(FOLD_KEY) || '{}');
  } catch (e) {
    return {};
  }
}

function writeFolds(folds) {
  try {
    localStorage.setItem(FOLD_KEY, JSON.stringify(folds));
  } catch (e) { /* private window — folding just won't be remembered */ }
}

function applyFold(section, folded) {
  const toggle = section.querySelector('[data-release-fold]');

  section.dataset.folded = folded ? 'yes' : 'no';
  toggle.setAttribute('aria-expanded', String(!folded));
  toggle.textContent = folded ? '▸' : '▾';
}

function bindReleases(root) {
  const sections = [...root.querySelectorAll('.release[data-release]')];

  if (!sections.length) return;

  const folds = readFolds();

  const remember = (name, folded) => {
    folds[name] = folded;
    writeFolds(folds);
  };

  for (const section of sections) {
    const name = section.dataset.release;
    const chosen = folds[name];
    applyFold(section, chosen === undefined ? 'finished' in section.dataset : chosen);

    section.querySelector('[data-release-fold]').onclick = () => {
      const folded = section.dataset.folded !== 'yes';
      applyFold(section, folded);
      remember(name, folded);
    };
  }

  for (const button of root.querySelectorAll('[data-fold-all]')) {
    button.onclick = () => {
      const folded = button.dataset.foldAll === 'yes';

      for (const section of sections) {
        applyFold(section, folded);
        remember(section.dataset.release, folded);
      }
    };
  }
}

/* ---------- picking merge requests out of the review queue ---------- */

async function toClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);

    return true;
  } catch (e) {
    // Clipboard access can be refused; a textarea + execCommand still works on localhost.
    const field = document.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();

    const ok = document.execCommand('copy');
    field.remove();

    return ok;
  }
}

function bindPicker(root) {
  for (const picker of root.querySelectorAll('[data-picker]')) {
    const scope = picker.closest('section') || root;
    const boxes = () => [...scope.querySelectorAll('.pick')];
    const picked = () => boxes().filter((box) => box.checked);
    const count = picker.querySelector('[data-pick-count]');
    const copy = picker.querySelector('[data-pick-copy]');
    const masters = [...picker.querySelectorAll('[data-pick-all]')];

    // A master with no value covers everything; one with a state covers that state alone.
    const scopeOf = (master) => boxes().filter(
      (box) => !master.dataset.pickAll || box.dataset.state === master.dataset.pickAll);

    const update = () => {
      const chosen = picked();
      count.textContent = chosen.length
        ? `${chosen.length} of ${count(boxes().length, 'MR')}`
        : 'nothing selected';
      copy.disabled = !chosen.length;

      for (const master of masters) {
        const scope = scopeOf(master);
        const taken = scope.filter((box) => box.checked).length;
        master.checked = taken > 0 && taken === scope.length;
        master.indeterminate = taken > 0 && taken < scope.length;
      }
    };

    for (const master of masters) {
      master.onchange = () => {
        for (const box of scopeOf(master)) box.checked = master.checked;

        update();
      };
    }

    scope.addEventListener('change', (event) => {
      if (event.target.classList.contains('pick')) update();
    });

    copy.onclick = async () => {
      const links = picked().map((box) => box.dataset.url);
      const ok = await toClipboard(links.join('\n'));
      toast(ok ? `Copied ${count(links.length, 'link')}`
               : 'The browser refused access to the clipboard', ok ? 'ok' : 'bad');
    };

    update();
  }
}

/* ---------- settings ---------- */

// A secret field is always empty on load, so an untouched one must not be sent: an absent
// key keeps what is stored, while an explicit empty string is what clears it.
function settingsValues(root) {
  const values = {};

  for (const field of root.querySelectorAll('[data-setting]')) {
    const value = field.value.trim();
    const secret = field.type === 'password';
    const cleared = root.querySelector(`[data-setting-clear="${field.dataset.setting}"]`)?.checked;

    if (cleared) values[field.dataset.setting] = '';
    else if (value || !secret) values[field.dataset.setting] = value;
  }

  return values;
}

function bindSettings(root) {
  const save = root.querySelector('[data-settings-save]');

  if (!save) return;

  save.addEventListener('click', async () => {
    save.disabled = true;
    save.setAttribute('aria-busy', 'true');

    const { data } = await post('/api/settings', {
      values: settingsValues(root),
      sync_secrets: root.querySelector('[data-settings-sync]').checked,
    });

    save.removeAttribute('aria-busy');
    save.disabled = false;

    if (!data.ok) {
      toast(`Not saved: ${(data.error || '').slice(0, 200)}`, 'bad', 9000);

      return;
    }

    toast(`Saved ${count(data.saved.length, 'setting')}`, 'ok');
    // Re-render so every field reports its stored state instead of what was typed into it.
    setTimeout(() => window.location.reload(), 600);
  });
}

function bind(root) {
  bindCopy(root);
  bindTempo(root);
  bindWeeks(root);
  bindPicker(root);
  bindSettings(root);
  bindReleases(root);
  bindOvertime(root);
}

/* ---------- overtime figure in the rail ---------- */

// Only an explicit choice is stored, as with the release folds: the block starts open, and a
// browser that was never told otherwise keeps it open.
const OVERTIME_KEY = 'work-hub-overtime-open';

function readOvertimeOpen() {
  try {
    return localStorage.getItem(OVERTIME_KEY) !== 'no';
  } catch (e) {
    return true;
  }
}

function writeOvertimeOpen(open) {
  try {
    localStorage.setItem(OVERTIME_KEY, open ? 'yes' : 'no');
  } catch (e) { /* private window — the choice just won't be remembered */ }
}

function applyOvertimeOpen(figure, open) {
  const toggle = figure.querySelector('[data-overtime-fold]');

  figure.dataset.open = open ? 'yes' : 'no';
  toggle.setAttribute('aria-expanded', String(open));
  toggle.querySelector('.caret').textContent = open ? '▾' : '▸';
}

// The hook is spelled out in full: the Tempo day editor already carries a [data-overtime]
// checkbox, and repaint() binds fragments, so a shorter name matched the wrong element.
function bindOvertime(root) {
  const figure = root.querySelector('[data-overtime-figure]');

  if (!figure) return;

  applyOvertimeOpen(figure, readOvertimeOpen());

  figure.querySelector('[data-overtime-fold]').addEventListener('click', () => {
    const open = figure.dataset.open !== 'yes';

    applyOvertimeOpen(figure, open);
    writeOvertimeOpen(open);
  });
}

// The rail lives outside every [data-fragment], so repaint() never reaches it. Only the
// numbers are swapped here: the container and its button stay, and with them the fold state
// and the click handler bound to it once at load.
function paintOvertime(data) {
  const figure = document.querySelector('[data-overtime-figure]');

  if (!figure || !data) return;

  figure.hidden = !data.months.length;
  figure.querySelector('[data-overtime-label]').textContent = `Overtime ${data.year}`.trim();
  figure.querySelector('[data-overtime-total]').textContent = `+${data.total} h`;
  figure.querySelector('[data-overtime-months]').innerHTML = data.months
    .map((month) => `<li><span>${month.label}</span><span class="num">+${month.hours} h</span></li>`)
    .join('');
}

/* ---------- sidebar (only collapsible on a narrow screen) ---------- */

function setNav(open) {
  const sidebar = document.getElementById('sidebar');
  const scrim = document.querySelector('.scrim');
  const toggle = document.querySelector('[data-nav-open]');

  if (!sidebar) return;

  sidebar.classList.toggle('open', open);
  if (scrim) scrim.hidden = !open;
  if (toggle) toggle.setAttribute('aria-expanded', String(open));
  document.body.style.overflow = open ? 'hidden' : '';
}

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') setNav(false);
});

// A link tap on the narrow layout should not leave the rail covering the page it opened.
document.addEventListener('click', (event) => {
  if (event.target.closest('.sidebar-nav a')) setNav(false);
});

applyTheme(readTheme());
bind(document);
