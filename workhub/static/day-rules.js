// Whether a Tempo day may be written — the rules alone, with no DOM in sight, so they can be
// exercised straight from Node (tests/test_day_rules.py). They mirror the skill's own guards:
// every entry on the 15-minute grid, and 8 h exactly unless the day is marked as a short one
// (partial) or as a long one (overtime) — each direction is its own opt-in, as in the skill.
const QUARTER = 0.25;

const round15 = (value) => Math.max(0, Math.round(value / QUARTER) * QUARTER);
const fmt = (value) => String(Number(value.toFixed(2)));

// Hour fields are text, not number, so a decimal comma is read rather than silently dropped —
// Chrome renders a number input per locale but reports "" for anything it dislikes.
function parseHours(raw) {
  const text = String(raw == null ? '' : raw).trim().replace(',', '.');

  if (!text) return 0;

  const value = Number(text);

  return Number.isFinite(value) && value >= 0 ? value : NaN;
}

function dayVerdict(hours, target, partial, overtime) {
  const broken = hours.some((h) => Number.isNaN(h));
  const counted = hours.filter((h) => h > 0);
  // Summing 0.25 steps drifts (7 x 0.25 = 1.7500000000000002), so compare rounded hours.
  const total = Number(counted.reduce((sum, h) => sum + h, 0).toFixed(2));
  const offGrid = counted.some((h) => Math.abs(h / QUARTER - Math.round(h / QUARTER)) > 1e-9);

  let problem = '';

  if (broken) problem = 'hours must be a number, e.g. 1.75';
  else if (!counted.length) problem = 'add at least one entry';
  else if (offGrid) problem = 'hours must be a multiple of 15 minutes';
  else if (total < target && !partial) problem = `${fmt(target - total)} h short of ${fmt(target)} h`;
  else if (total > target && !overtime) problem = `${fmt(total - target)} h over ${fmt(target)} h — tick "overtime"`;

  let note = 'ready to write';

  if (problem) note = problem;
  else if (total < target) note = `short day: ${fmt(total)} h`;
  else if (total > target) note = `overtime: ${fmt(total)} h`;

  return { total, problem, note, ok: !problem };
}

// Mirrors workhub.text.count — the same rule, on the other side of the wire.
function count(n, one, many) {
  return `${n} ${n === 1 ? one : (many || `${one}s`)}`;
}

if (typeof module !== 'undefined') {
  module.exports = { QUARTER, round15, fmt, parseHours, dayVerdict, count };
}
