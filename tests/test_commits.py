import unittest

from . import context  # noqa: F401
from workhub import render, sources

ROW = {
    "tickets": ["ABC-1", "ABC-2"],
    "jira": "Defect: Something",
    "commits": [{"sha": "1234abcd", "time": "09:07", "subject": "fix(ABC-1, ABC-2): Focus the first item"}],
    "state": "followup_draft",
    "tone": "wait",
    "status": "dociągnięcie · draft MR",
    "ref": "!817 · origin/fix/ABC-1",
    "mr": {"iid": 817, "web_url": "https://example/817", "state": "opened", "draft": True,
           "target_branch": "develop", "title": "Draft: fix(ABC-1)"},
    "scope": "Renamed <code>hasTvPreferredFocus</code> <script>alert(1)</script>",
    "plain": "Nothing was focused <b>at first</b>.",
}

COMMITS = {"main": {
    "generated_at": "2026-10-27T10:55:00",
    "days": [{"date": "2026-10-27", "label": "wt 27.10"}],
    "sections": [
        {"day": "2026-10-27", "day_label": "wt 27.10", "repo": "team-portal", "commits": 2,
         "rows": [ROW, dict(ROW, tickets=["ABC-3"], state="merged", tone="ok", mr=None, ref="ad83d2b5")]},
    ],
}}


class CommitsPanel(unittest.TestCase):
    body = staticmethod(render.RENDERERS["commits"][0])
    headline = staticmethod(render.RENDERERS["commits"][1])

    def test_runs_the_skill_json_command_with_room_for_claude(self):
        panel = sources.BY_ID["commits"]

        self.assertEqual(panel.commands[0].resolve()[-2:], [sources.skill("daily-commit-summary", "live.py"), "json"])
        self.assertGreaterEqual(panel.timeout, 600)

    def test_rows_show_tickets_prose_state_and_mr(self):
        html = self.body(COMMITS)

        self.assertIn("Tue 27.10 · team-portal", html)
        self.assertIn("ABC-2", html)
        self.assertIn("follow-up · draft MR", html)
        self.assertIn("!817", html)
        self.assertIn("on develop", html)
        self.assertIn("ad83d2b5", html)

    def test_only_code_tags_survive_from_the_skill_prose(self):
        html = self.body(COMMITS)

        self.assertIn("<code>hasTvPreferredFocus</code>", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>", html)

    def test_headline_counts_tickets_not_rows(self):
        html = self.headline(COMMITS)

        self.assertIn("2 commits", html)
        self.assertIn("3 tickets", html)
        self.assertIn("1 on develop", html)
        self.assertIn("2 waiting", html)

    def test_payload_from_the_old_text_commands_asks_for_a_refresh(self):
        old = {"commits": "===== repo =====", "merge": ""}

        self.assertIn("Refresh", self.body(old))
        self.assertIn("refresh needed", self.headline(old))


if __name__ == "__main__":
    unittest.main()
