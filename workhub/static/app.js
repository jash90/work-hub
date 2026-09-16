// Refresh buttons, theme, clipboard briefs and the Tempo day editor.
// Every POST carries the start-up CSRF token the page holds in <html data-csrf>.
const CSRF = document.documentElement.dataset.csrf;

/* ---------- theme ---------- */

const THEMES = ['auto', 'light', 'dark'];
const THEME_GLYPH = { auto: '◐', light: '☀', dark: '☾' };
const THEME_TITLE = { auto: 'Motyw: automatyczny', light: 'Motyw: jasny', dark: 'Motyw: ciemny' };

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
      button.textContent = on ? 'Odświeżam' : 'Odśwież';
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

      if (panel.error && panel.fetched_at) toast(`${panel.label}: dane starsze, odświeżenie nie przeszło`, 'bad', 7000);
      else if (panel.error) toast(`${panel.label}: ${panel.error.slice(0, 160)}`, 'bad', 8000);

      if (document.querySelector('.grid')) refreshedCards = true;
    }
  }

  if (refreshedCards) window.location.reload();
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
  toast(all ? 'Odświeżam wszystkie panele…' : 'Odświeżam…');
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
      toast(ok ? 'Skopiowane do schowka' : 'Przeglądarka nie dała dostępu do schowka',
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
    hours: readHours(row.querySelector('.hours')),
  }));
}

function refreshDay(day) {
  const all = dayEntries(day);
  const target = Number(day.dataset.target);
  const partial = day.querySelector('[data-partial]').checked;
  const verdict = dayVerdict(all.map((e) => e.hours), target, partial);

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
  submit.title = verdict.problem || 'Zapisze worklogi w Tempo';

  return { entries: all.filter((e) => e.hours > 0), total: verdict.total, partial };
}

function entriesString(entries) {
  return entries.map((e) => `${e.key}=${fmt(e.hours)}`).join(',');
}

function addEntryRow(day, key, hours) {
  const body = day.querySelector('.entries-table tbody');
  const row = document.createElement('tr');
  row.className = 'entry';
  row.dataset.entry = '';
  row.innerHTML = `
    <td class="entry-key"><a class="key" href="https://jira.example.com/browse/${key}" target="_blank" rel="noopener">${key}</a></td>
    <td class="entry-summary"><span class="muted">dodane ręcznie</span></td>
    <td class="entry-commits"></td>
    <td class="entry-hours">
      <div class="stepper">
        <button type="button" class="step" data-step="-0.25" aria-label="mniej o 15 minut">−</button>
        <input type="text" class="hours" value="${fmt(hours)}" inputmode="decimal" autocomplete="off">
        <button type="button" class="step" data-step="0.25" aria-label="więcej o 15 minut">+</button>
      </div>
    </td>
    <td class="entry-drop"><button type="button" class="ghost" data-drop aria-label="usuń pozycję">×</button></td>`;
  body.appendChild(row);
}

function bindTempo(root) {
  for (const day of root.querySelectorAll('.day')) {
    const update = () => refreshDay(day);

    day.addEventListener('input', (event) => {
      if (event.target.classList.contains('hours')) update();
    });

    day.addEventListener('change', (event) => {
      if (event.target.matches('[data-partial]')) update();

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
          toast('Klucz ticketu wygląda jak ABC-1234', 'bad');

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

      if (log) await submitDay(day, log);
      if (undo) await undoDay(day, undo);
    });

    update();
  }
}

async function submitDay(day, button) {
  const { entries, total, partial } = refreshDay(day);

  if (day.dataset.valid !== 'yes') return;

  const listing = entries.map((e) => `  ${e.key} — ${fmt(e.hours)} h`).join('\n');
  const label = partial && total !== Number(day.dataset.target) ? ' (niepełny dzień)' : '';

  if (!confirm(`Zapisać worklogi w Tempo za ${day.dataset.day}${label}?\n\n${listing}\n\nRazem ${fmt(total)} h. To jest realny POST do Jiry.`)) return;

  button.disabled = true;
  button.setAttribute('aria-busy', 'true');

  const { data } = await post('/api/tempo/log', {
    day: day.dataset.day,
    entries: entriesString(entries),
    allow_partial: partial,
    confirm: true,
  });

  button.removeAttribute('aria-busy');
  button.disabled = false;
  toast(data.ok ? `Zalogowano ${day.dataset.day} — ${fmt(total)} h` : `Odmowa: ${(data.output || data.error || '').slice(0, 200)}`,
        data.ok ? 'ok' : 'bad', data.ok ? 4000 : 9000);
}

async function undoDay(day, button) {
  if (!confirm(`Cofnąć worklogi za ${day.dataset.day}? Skasuje je z Jiry.`)) return;

  button.disabled = true;
  button.setAttribute('aria-busy', 'true');

  const { data } = await post('/api/tempo/undo', { day: day.dataset.day, confirm: true });

  button.removeAttribute('aria-busy');
  button.disabled = false;
  toast(data.ok ? `Cofnięto ${day.dataset.day}` : `Nie udało się: ${(data.output || '').slice(0, 200)}`,
        data.ok ? 'ok' : 'bad', data.ok ? 4000 : 9000);
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
    const all = picker.querySelector('[data-pick-all]');

    const update = () => {
      const chosen = picked();
      count.textContent = chosen.length
        ? `${chosen.length} z ${plural(boxes().length, 'MR-a', 'MR-ów', 'MR-ów')}`
        : 'nic nie zaznaczone';
      copy.disabled = !chosen.length;
      all.checked = chosen.length > 0 && chosen.length === boxes().length;
      all.indeterminate = chosen.length > 0 && chosen.length < boxes().length;
    };

    all.onchange = () => {
      for (const box of boxes()) box.checked = all.checked;

      update();
    };

    scope.addEventListener('change', (event) => {
      if (event.target.classList.contains('pick')) update();
    });

    copy.onclick = async () => {
      const links = picked().map((box) => box.dataset.url);
      const ok = await toClipboard(links.join('\n'));
      toast(ok ? `Skopiowano ${plural(links.length, 'link', 'linki', 'linków')}`
               : 'Przeglądarka nie dała dostępu do schowka', ok ? 'ok' : 'bad');
    };

    update();
  }
}

function bind(root) {
  bindCopy(root);
  bindTempo(root);
  bindPicker(root);
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
