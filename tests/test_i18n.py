"""Two interface languages, and Polish skill data turned English for the English one."""
import ast
import glob
import json
import os
import re
import shutil
import subprocess
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from . import context  # noqa: F401
from workhub import ROOT, config, server, sources, text, translate
from workhub.catalog import POLISH
from workhub.render import gitlab, layout, reports, work

STATIC = os.path.join(ROOT, "workhub", "static")


def interface_strings():
    """Every English phrase the interface can show: t() literals, labels, headers, JS."""
    found = set()

    for name in glob.glob(os.path.join(ROOT, "workhub", "**", "*.py"), recursive=True):
        source = open(name, encoding="utf-8").read()

        for match in re.finditer(r'\bt\(\s*((?:"(?:[^"\\]|\\.)*"\s*)+)', source):
            found.add(ast.literal_eval("(%s)" % match.group(1)))

        for match in re.finditer(r"table\(\[([^\]]*)\]", source):
            found.update(ast.literal_eval("[%s]" % match.group(1)))

    for name in glob.glob(os.path.join(STATIC, "*.js")):
        for match in re.finditer(r"\bt\('((?:[^'\\]|\\.)*)'", open(name, encoding="utf-8").read()):
            found.add(json.loads('"%s"' % match.group(1).replace('"', '\\"').replace("\\'", "'")))

    for panel in sources.PANELS:
        found.update((panel.label, panel.blurb))
        found.update(c.fallback_note for c in panel.commands if c.fallback_note)

    for setting in config.SETTINGS:
        found.update((setting.label, setting.note))

    found.update(sources.GROUP_LABELS.values(), config.GROUPS, work.REVIEW_LABELS.values(),
                 layout.BUCKET_LABELS.values(), reports.COMMIT_STATES.values(),
                 gitlab.STATE_PICK_LABELS.values())

    # Product names read the same in both languages.
    return {s for s in found if s and "Personal Access Token" not in s and s != "Jira"}


class Polish(unittest.TestCase):
    def setUp(self):
        text.use(text.POLISH_LANG)

    def tearDown(self):
        text.use(text.ENGLISH)

    def test_every_interface_string_has_a_polish_entry(self):
        missing = sorted(s for s in interface_strings() if s not in POLISH)

        self.assertEqual([], missing)

    def test_counts_take_the_three_polish_forms(self):
        self.assertEqual("1 task", text.count(1, "task"))
        self.assertEqual("3 taski", text.count(3, "task"))
        self.assertEqual("5 tasków", text.count(5, "task"))
        self.assertEqual("12 MR-ów", text.count(12, "MR"))

    def test_ago_takes_the_accusative(self):
        self.assertEqual("1 minutę temu", text.ago_phrase(1, "minute"))
        self.assertEqual("od 1 dnia", text.days_ago(1))
        self.assertEqual("od 4 dni", text.days_ago(4))

    def test_dates_are_named_in_polish(self):
        self.assertEqual("śr 28.10", text.short_date("2026-10-28"))
        self.assertEqual("Październik", layout.month_name("2026-10"))

    def test_the_page_is_polish_and_carries_the_catalogue(self):
        html = layout.page("t", "", "", "csrf")

        self.assertIn('<html lang="pl"', html)
        self.assertIn("Odśwież wszystko", html)
        self.assertIn("window.WORK_HUB_STRINGS", html)
        self.assertIn('data-lang="en"', html)

    def test_skill_data_is_left_in_its_own_language(self):
        self.assertEqual("nierozwiązane wątki", layout.esc("nierozwiązane wątki"))


class English(unittest.TestCase):
    def setUp(self):
        text.use(text.ENGLISH)
        self.saved = dict(translate._known())

    def tearDown(self):
        translate._known().clear()
        translate._known().update(self.saved)

    def test_the_page_offers_polish_and_embeds_no_catalogue(self):
        html = layout.page("t", "", "", "csrf")

        self.assertIn('<html lang="en"', html)
        self.assertIn('data-lang="pl"', html)
        self.assertNotIn("WORK_HUB_STRINGS =", html)

    def test_polish_prose_is_recognised_and_names_are_not_mistaken_for_it(self):
        self.assertTrue(translate.looks_polish("Draft bez sygnału gotowości"))
        self.assertTrue(translate.looks_polish("krs przed kan"))
        self.assertFalse(translate.looks_polish("https://example.com/w/a-z"))
        self.assertFalse(translate.looks_polish("Waiting on the author"))

    def test_a_translated_string_is_shown_in_english(self):
        translate.english("nierozwiązane wątki")
        translate.flush(lambda texts: ["unresolved threads" for _ in texts])

        self.assertEqual("unresolved threads", layout.esc("nierozwiązane wątki"))

    def test_an_unknown_string_shows_as_it_is_until_translated(self):
        self.assertEqual("coś zupełnie nowego", translate.english("coś zupełnie nowego"))
        self.assertTrue(translate.has_pending())

        translate.flush(lambda texts: ["something entirely new" for _ in texts])

        self.assertEqual("something entirely new", translate.english("coś zupełnie nowego"))

    def test_a_failed_or_misshapen_answer_caches_nothing(self):
        def broken(texts):
            raise RuntimeError("model down")

        translate.english("jeszcze nie przetłumaczone")
        self.assertEqual(0, translate.flush(broken))

        translate.english("jeszcze nie przetłumaczone")
        self.assertEqual(0, translate.flush(lambda texts: []))

        self.assertEqual("jeszcze nie przetłumaczone", translate.english("jeszcze nie przetłumaczone"))


class LanguageCookie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.Handler.hub = server.Hub()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def page(self, cookie=None):
        request = urllib.request.Request("http://127.0.0.1:%d/" % self.httpd.server_address[1],
                                         headers={"Cookie": cookie} if cookie else {})

        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode()

    def test_english_without_a_cookie(self):
        self.assertIn('<html lang="en"', self.page())

    def test_polish_with_the_cookie(self):
        self.assertIn('<html lang="pl"', self.page("work-hub-lang=pl"))

    def test_an_unknown_language_falls_back_to_english(self):
        self.assertIn('<html lang="en"', self.page("work-hub-lang=xx"))


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Browser(unittest.TestCase):
    DRIVER = """
global.document = {documentElement: {lang: 'pl'}};
global.window = {WORK_HUB_STRINGS: %s};
const {t, count} = require(%s);
process.stdout.write(JSON.stringify([t('Saved {0} — {1} h', '2026-10-28', 8),
  count(1, 'MR'), count(3, 'MR'), count(5, 'MR'), count(2, 'unknown')]));
"""

    def test_the_browser_reads_the_same_catalogue(self):
        from workhub.catalog import NOUNS

        blob = json.dumps({"strings": POLISH, "nouns": NOUNS}, ensure_ascii=False)
        driver = self.DRIVER % (blob, json.dumps(os.path.join(STATIC, "i18n.js")))
        out = subprocess.run(["node", "-e", driver], capture_output=True, text=True, timeout=30)

        self.assertEqual(["Zapisano 2026-10-28 — 8 h", "1 MR", "3 MR-y", "5 MR-ów", "2 unknowns"],
                         json.loads(out.stdout), out.stderr)


if __name__ == "__main__":
    unittest.main()
