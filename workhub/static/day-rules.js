// Whether a Tempo day may be written — the rules alone, with no DOM in sight, so they can be
// exercised straight from Node (tests/test_day_rules.py). They mirror the skill's own guards:
// every entry on the 15-minute grid, and 8 h exactly unless the day is marked as a short one
// (partial) or as a long one (overtime) — each direction is its own opt-in, as in the skill.
const QUARTER = 0.25;
// In the page i18n.js is loaded first and its functions are globals; Node has to ask for them.
const words = typeof module !== 'undefined' ? require('./i18n.js') : { t };

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

  if (broken) problem = words.t('hours must be a number, e.g. 1.75');
  else if (!counted.length) problem = words.t('add at least one entry');
  else if (offGrid) problem = words.t('hours must be a multiple of 15 minutes');
  else if (total < target && !partial) problem = words.t('{0} h short of {1} h', fmt(target - total), fmt(target));
  else if (total > target && !overtime) problem = words.t('{0} h over {1} h — tick "overtime"', fmt(total - target), fmt(target));

  let note = words.t('ready to write');

  if (problem) note = problem;
  else if (total < target) note = words.t('short day: {0} h', fmt(total));
  else if (total > target) note = words.t('overtime: {0} h', fmt(total));

  return { total, problem, note, ok: !problem };
}

if (typeof module !== 'undefined') {
  module.exports = { QUARTER, round15, fmt, parseHours, dayVerdict };
}
