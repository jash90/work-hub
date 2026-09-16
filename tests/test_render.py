import unittest

from . import context  # noqa: F401
from workhub import render
from workhub.render import layout

DASHBOARD = {"main": {
    "min_approvals": 2,
    "tasks": [{"key": "ABC-1", "status": "Backlog", "summary": "Coś", "days": 1,
               "release_name": "Apple_Android TV 12.0.0", "bucket": 1,
               "mrs": [{"iid": "676", "web_url": "https://example/676"}]}],
    "ready": [],
    "other_mrs": [{"iid": "721", "repo": "team-portal", "title": "fix: coś",
                   "web_url": "https://example/721", "approval_count": 1, "unresolved": 2,
                   "blocking": ["pipeline w toku"], "draft": False}],
    "review": {"summary": {"total": 3, "mrs": 2, "on_me": 1, "counts": {"waiting_for_me": 1}},
               "threads": [{"kind": "waiting_for_me", "iid": "1411", "repo": "team-mobile",
                            "file": "index.tsx", "line": 88, "excerpt": "pytanie",
                            "url": "https://example/1411", "waited_days": 1}]},
    "drift": [{"kind": "not_in_review", "label": "ABC-1", "status": "Backlog",
               "detail": "podnieś status", "url": "https://example/676"}],
}}


class Rendering(unittest.TestCase):
    def test_dashboard_shows_its_numbers(self):
        html = render.RENDERERS["dashboard"][0](DASHBOARD)

        self.assertIn("ABC-1", html)
        self.assertIn("!721", html)
        self.assertIn("jutro", html)
        self.assertIn("2 wątki", html)

    def test_headline_counts_agree_with_the_payload(self):
        self.assertIn("1 task do zrobienia", render.RENDERERS["dashboard"][1](DASHBOARD))
        self.assertIn("1 uwaga u mnie", render.RENDERERS["dashboard"][1](DASHBOARD))

    def test_every_panel_has_a_renderer(self):
        from workhub import sources

        self.assertEqual(sorted(p.id for p in sources.PANELS), sorted(render.RENDERERS))

    def test_a_broken_payload_degrades_to_a_banner(self):
        html = render.body("dashboard", {"payload": {"main": "nie ten kształt"}})

        self.assertIn("Nie udało się wyrenderować", html)

    def test_missing_payload_asks_for_a_refresh(self):
        self.assertIn("Odśwież", render.body("dashboard", {"payload": None}))


class Navigation(unittest.TestCase):
    def test_sidebar_lists_every_panel_exactly_once(self):
        from workhub import sources

        html = layout.sidebar("tempo")

        for panel in sources.PANELS:
            self.assertEqual(1, html.count('href="/p/%s"' % panel.id), panel.id)

    def test_sidebar_marks_the_open_panel(self):
        self.assertIn('href="/p/tempo" class="on"', layout.sidebar("tempo"))

    def test_sidebar_is_part_of_the_page_not_a_dialog(self):
        """It is a permanent rail; only the narrow layout hides it, and that is CSS."""
        html = layout.sidebar("tempo")

        self.assertNotIn("aria-modal", html)
        self.assertNotIn('<aside class="sidebar" id="sidebar" hidden', html)

    def test_header_names_the_open_panel(self):
        self.assertEqual("Tempo", layout.crumb("tempo"))
        self.assertEqual("Przegląd", layout.crumb(""))


class Escaping(unittest.TestCase):
    def test_summary_is_escaped(self):
        payload = {"main": dict(DASHBOARD["main"],
                                tasks=[dict(DASHBOARD["main"]["tasks"][0],
                                            summary="<script>alert(1)</script>")])}
        html = render.RENDERERS["dashboard"][0](payload)

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class Notes(unittest.TestCase):
    def test_fallback_note_is_shown(self):
        html = layout.notes({"_notes": {"main": "Pełny skład niedostępny"}})

        self.assertIn("Pełny skład niedostępny", html)
