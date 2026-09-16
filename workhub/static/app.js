// Refresh buttons, clipboard briefs and the two Tempo write actions.
// Everything POSTs with the start-up CSRF token the page carries in <html data-csrf>.
const CSRF = document.documentElement.dataset.csrf;

function toast(text, ms = 3200) {
  const node = document.createElement('div');
  node.className = 'toast';
  node.textContent = text;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), ms);
}

async function post(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF': CSRF },
    body: JSON.stringify(body),
  });

  return { status: response.status, data: await response.json().catch(() => ({})) };
}

async function state() {
  const response = await fetch('/api/state');

  return response.json();
}

// Poll until the named panels stop running, then bring their markup up to date.
async function follow(ids) {
  const pending = new Set(ids);

  while (pending.size) {
    await new Promise((resolve) => setTimeout(resolve, 900));
    const now = await state();

    for (const panel of now.panels) {
      if (!pending.has(panel.id) || panel.running) continue;

      pending.delete(panel.id);
      await repaint(panel);
    }
  }
}

async function repaint(panel) {
  const host = document.querySelector(`[data-panel="${panel.id}"] [data-fragment]`);

  if (host) {
    host.innerHTML = await (await fetch(`/p/${panel.id}/fragment`)).text();
    bindCopy(host);
    bindTempo(host);
  }

  if (document.querySelector('.grid')) window.location.reload();
}

function markRunning(ids) {
  for (const id of ids) {
    for (const button of document.querySelectorAll(`[data-refresh="${id}"]`)) {
      button.disabled = true;
      button.textContent = 'Odświeżam…';
    }
  }
}

document.addEventListener('click', async (event) => {
  const one = event.target.closest('[data-refresh]');
  const all = event.target.closest('[data-refresh-all]');

  if (!one && !all) return;

  const body = all ? { all: true } : { panel: one.dataset.refresh };
  const { data } = await post('/api/refresh', body);
  const ids = data.started || [];

  markRunning(ids);
  toast(all ? 'Odświeżam wszystkie panele…' : 'Odświeżam…');
  await follow(ids);
});

function bindCopy(root) {
  for (const button of root.querySelectorAll('[data-copy]')) {
    button.onclick = async () => {
      const text = new TextDecoder().decode(
        Uint8Array.from(atob(button.dataset.copy), (c) => c.charCodeAt(0)),
      );
      await navigator.clipboard.writeText(text);
      toast('Skopiowane do schowka');
    };
  }
}

function bindTempo(root) {
  for (const button of root.querySelectorAll('[data-tempo-log]')) {
    button.onclick = async () => {
      const day = button.dataset.tempoLog;
      const field = root.querySelector(`[data-entries="${day}"]`);
      const entries = field ? field.value.trim() : '';

      if (!confirm(`Zapisać worklogi w Jirze za ${day}?\n\n${entries}\n\nTo jest realny POST do Tempo.`)) return;

      button.disabled = true;
      const { data } = await post('/api/tempo/log', { day, entries, confirm: true });
      button.disabled = false;
      toast(data.ok ? `Zalogowano ${day}` : `Odmowa: ${(data.output || data.error || '').slice(0, 180)}`, 7000);
    };
  }

  for (const button of root.querySelectorAll('[data-tempo-undo]')) {
    button.onclick = async () => {
      const day = button.dataset.tempoUndo;

      if (!confirm(`Cofnąć worklogi za ${day}? Skasuje je z Jiry.`)) return;

      button.disabled = true;
      const { data } = await post('/api/tempo/undo', { day, confirm: true });
      button.disabled = false;
      toast(data.ok ? `Cofnięto ${day}` : `Nie udało się: ${(data.output || '').slice(0, 180)}`, 7000);
    };
  }
}

bindCopy(document);
bindTempo(document);
