// The browser half of workhub/text.py. The Polish catalogue is not repeated here: a Polish
// page embeds the server's own table as window.WORK_HUB_STRINGS, and an English page embeds
// nothing, so every phrase falls through to the English it is written in.
// Plain function declarations, so day-rules.js reaches them as globals in the page and
// through require() under Node, where the tests run in English.
var WORK_HUB_I18N = (typeof window !== 'undefined' && window.WORK_HUB_STRINGS) || { strings: {}, nouns: {} };
var WORK_HUB_LANG = typeof document !== 'undefined' ? document.documentElement.lang || 'en' : 'en';

// `{0}`, `{1}` mark where the arguments go, in whichever order the language needs them.
function t(text, ...args) {
  const template = WORK_HUB_I18N.strings[text] ?? text;

  return template.replace(/\{(\d+)\}/g, (_, at) => String(args[Number(at)]));
}

// Polish has three forms; Intl.PluralRules picks one/few/many the way redge_work.polish does.
const PLURAL_FORMS = { one: 0, few: 1, many: 2 };

function count(n, one, many) {
  const forms = WORK_HUB_I18N.nouns[one];

  if (forms) {
    const form = new Intl.PluralRules(WORK_HUB_LANG).select(n);

    return `${n} ${forms[PLURAL_FORMS[form] ?? 2]}`;
  }

  return `${n} ${n === 1 ? one : (many || `${one}s`)}`;
}

if (typeof module !== 'undefined') {
  module.exports = { t, count };
}
