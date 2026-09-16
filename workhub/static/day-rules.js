// Whether a Tempo day may be written — the rules alone, with no DOM in sight, so they can be
// exercised straight from Node (tests/test_day_rules.py). They mirror the skill's own guards:
// every entry on the 15-minute grid, and 8 h exactly unless the day is marked partial.
const QUARTER = 0.25;

const round15 = (value) => Math.max(0, Math.round(value / QUARTER) * QUARTER);
const fmt = (value) => String(Number(value.toFixed(2)));

// Hour fields are text, not number, so a Polish decimal comma is read rather than silently
// dropped — Chrome renders a number input per locale but reports "" for anything it dislikes.
function parseHours(raw) {
  const text = String(raw == null ? '' : raw).trim().replace(',', '.');

  if (!text) return 0;

  const value = Number(text);

  return Number.isFinite(value) && value >= 0 ? value : NaN;
}

function dayVerdict(hours, target, partial) {
  const broken = hours.some((h) => Number.isNaN(h));
  const counted = hours.filter((h) => h > 0);
  // Summing 0.25 steps drifts (7 x 0.25 = 1.7500000000000002), so compare rounded hours.
  const total = Number(counted.reduce((sum, h) => sum + h, 0).toFixed(2));
  const offGrid = counted.some((h) => Math.abs(h / QUARTER - Math.round(h / QUARTER)) > 1e-9);

  let problem = '';

  if (broken) problem = 'godziny muszą być liczbą, np. 1,75';
  else if (!counted.length) problem = 'dodaj przynajmniej jedną pozycję';
  else if (offGrid) problem = 'godziny muszą być wielokrotnością 15 minut';
  else if (total !== target && !partial) problem = `brakuje ${fmt(target - total)} h do ${fmt(target)} h`;

  const note = problem
    || (partial && total !== target ? `niepełny dzień: ${fmt(total)} h` : 'gotowe do zapisu');

  return { total, problem, note, ok: !problem };
}

// Mirrors redge_work.polish.plural — the same rule, on the other side of the wire.
function plural(n, one, few, many) {
  if (n === 1) return `${n} ${one}`;

  const teens = n % 100;
  const last = n % 10;

  return `${n} ${last >= 2 && last <= 4 && !(teens >= 12 && teens <= 14) ? few : many}`;
}

if (typeof module !== 'undefined') {
  module.exports = { QUARTER, round15, fmt, parseHours, dayVerdict, plural };
}
