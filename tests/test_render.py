import os
import unittest

from . import context  # noqa: F401
from workhub import overtime, render, store
from workhub.render import layout, releases

DASHBOARD = {"main": {
    "min_approvals": 2,
    "tasks": [{"key": "ABC-1", "status": "Backlog", "summary": "Something", "days": 1,
               "release_name": "Apple_Android TV 12.0.0", "bucket": 1,
               "mrs": [{"iid": "676", "web_url": "https://example/676"}]}],
    "ready": [],
    "other_mrs": [{"iid": "721", "repo": "team-portal", "title": "fix: something",
                   "web_url": "https://example/721", "approval_count": 1, "unresolved": 2,
                   "blocking": ["pipeline running"], "draft": False}],
    "review": {"summary": {"total": 3, "mrs": 2, "on_me": 1, "counts": {"waiting_for_me": 1}},
               "threads": [{"kind": "waiting_for_me", "iid": "1411", "repo": "team-mobile",
                            "file": "index.tsx", "line": 88, "excerpt": "a question",
                            "url": "https://example/1411", "waited_days": 1}]},
    "drift": [{"kind": "not_in_review", "label": "ABC-1", "status": "Backlog",
               "detail": "raise the status", "url": "https://example/676"}],
}}


class Rendering(unittest.TestCase):
    def test_dashboard_shows_its_numbers(self):
        html = render.RENDERERS["dashboard"][0](DASHBOARD)

        self.assertIn("ABC-1", html)
        self.assertIn("!721", html)
        self.assertIn("tomorrow", html)
        self.assertIn("2 threads", html)

    def test_headline_counts_agree_with_the_payload(self):
        self.assertIn("1 task to do", render.RENDERERS["dashboard"][1](DASHBOARD))
        self.assertIn("1 comment on me", render.RENDERERS["dashboard"][1](DASHBOARD))

    def test_every_panel_has_a_renderer(self):
        from workhub import sources

        self.assertEqual(sorted(p.id for p in sources.PANELS), sorted(render.RENDERERS))

    def test_a_broken_payload_degrades_to_a_banner(self):
        html = render.body("dashboard", {"payload": {"main": "not the expected shape"}})

        self.assertIn("Could not render", html)

    def test_missing_payload_asks_for_a_refresh(self):
        self.assertIn("Refresh", render.body("dashboard", {"payload": None}))


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
        self.assertEqual("Overview", layout.crumb(""))


TEMPO = {
    "gaps": "# none",
    "propose": {"plan": [{"day": "2026-09-10", "weekday": "Thu", "total_hours": 8.0,
                          "entries": [{"key": "ABC-9", "summary": "Proposal", "hours": 8.0,
                                       "seconds": 28800, "commits": 3, "subjects": ["x"]}]}],
                "skipped": []},
    "worklogs": {"from": "2026-09-07", "to": "2026-09-13", "days": [
        {"day": "2026-09-07", "weekday": "Mon", "workday": True, "total_hours": 8.0,
         "entries": [{"id": 1404459, "key": "ABC-1", "summary": "Logged",
                      "hours": 8.0, "seconds": 28800, "comment": ""}]},
        {"day": "2026-09-08", "weekday": "Tue", "workday": True, "total_hours": 0, "entries": []},
        {"day": "2026-09-09", "weekday": "Wed", "workday": True, "total_hours": 0, "entries": []},
        {"day": "2026-09-10", "weekday": "Thu", "workday": True, "total_hours": 0, "entries": []},
        {"day": "2026-09-11", "weekday": "Fri", "workday": True, "total_hours": 0, "entries": []},
        {"day": "2026-09-12", "weekday": "Sat", "workday": False, "total_hours": 0, "entries": []},
        {"day": "2026-09-13", "weekday": "Sun", "workday": False, "total_hours": 0, "entries": []},
    ]},
}


class TempoPanel(unittest.TestCase):
    def html(self, payload=None):
        return render.RENDERERS["tempo"][0](payload or TEMPO)

    def test_a_logged_day_is_editable_in_place(self):
        html = self.html()

        self.assertIn('data-worklog-id="1404459"', html)
        self.assertIn('data-endpoint="/api/tempo/replace"', html)
        self.assertIn("Save changes", html)

    def test_a_day_with_a_proposal_still_goes_through_log(self):
        html = self.html()

        self.assertIn('data-endpoint="/api/tempo/log"', html)
        self.assertIn("ABC-9", html)

    def test_a_day_has_exactly_one_editor(self):
        """Two cards for one day would mean two truths about it, and the stale one submits too."""
        for day in ("2026-09-07", "2026-09-10"):
            self.assertEqual(1, self.html().count('data-day="%s"' % day), day)

    def test_both_directions_are_opt_in(self):
        html = self.html()

        self.assertIn("data-partial", html)
        self.assertIn("data-overtime", html)

    def test_a_weekend_is_shown_but_not_editable(self):
        html = self.html()

        self.assertIn("day off", html)
        self.assertNotIn('data-day="2026-09-12"', html)

    def test_days_without_worklogs_still_appear(self):
        """A week missing its quiet days renders as Monday, Tuesday, Thursday."""
        self.assertIn('data-day="2026-09-09"', self.html())

    def test_the_week_carries_its_own_label_and_total(self):
        html = self.html()

        self.assertIn('data-label="September 7 – September 13"', html)
        self.assertIn('data-total="8 h / 40 h"', html)

    def test_it_still_renders_before_the_first_worklog_refresh(self):
        html = self.html({"gaps": "", "propose": TEMPO["propose"]})

        self.assertIn("ABC-9", html)
        self.assertNotIn("data-weeks", html)


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
        html = layout.notes({"_notes": {"main": "The full team is unavailable"}})

        self.assertIn("The full team is unavailable", html)


class Settings(unittest.TestCase):
    """The settings screen. Its one hard rule: a stored secret never reaches the HTML."""

    def setUp(self):
        from workhub import config

        self.config = config
        self.addCleanup(self.clear)
        self.clear()

    def clear(self):
        import os

        self.config._cache.update(stamp=None, values={})

        if os.path.exists(self.config.ENV_PATH):
            os.unlink(self.config.ENV_PATH)

    def html(self):
        from workhub.render import settings

        return settings.page_body()

    def test_a_stored_token_is_described_never_printed(self):
        self.config.save({"JIRA_TOKEN": "very-secret-4f2c"})
        html = self.html()

        self.assertNotIn("very-secret", html)
        self.assertIn("…4f2c", html)

    def test_a_secret_field_comes_up_empty_so_a_save_cannot_echo_it_back(self):
        self.config.save({"JIRA_TOKEN": "secret"})
        html = self.html()

        self.assertIn('type="password"', html)
        self.assertNotIn('value="secret"', html)

    def test_every_setting_has_a_field(self):
        html = self.html()

        for setting in self.config.SETTINGS:
            self.assertIn('data-setting="%s"' % setting.key, html)

    def test_clearing_is_offered_only_for_a_value_that_exists(self):
        self.assertIn("disabled", self.html())

        self.config.save({"JIRA_TOKEN": "x"})

        self.assertIn('data-setting-clear="JIRA_TOKEN"', self.html())

    def test_the_shell_renders_for_a_screen_that_is_not_a_panel(self):
        html = layout.page("t", "settings", "<p>x</p>", "csrf")

        self.assertIn('href="/settings" class="on"', html)
        self.assertIn("Settings", layout.crumb("settings"))


class TicketLinks(unittest.TestCase):
    def setUp(self):
        from workhub import config

        self.config = config
        self.addCleanup(self.clear)
        self.clear()

    def clear(self):
        import os

        self.config._cache.update(stamp=None, values={})

        if os.path.exists(self.config.ENV_PATH):
            os.unlink(self.config.ENV_PATH)

    def test_a_key_links_to_the_configured_jira(self):
        self.config.save({"JIRA_BASE_URL": "https://jira.example.com/"})

        self.assertIn('href="https://jira.example.com/browse/ABC-1"', layout.ticket_link("ABC-1"))

    def test_without_an_address_the_key_is_plain_text_not_a_broken_link(self):
        self.assertNotIn("href", layout.ticket_link("ABC-1"))
        self.assertIn("ABC-1", layout.ticket_link("ABC-1"))


class ReleaseWarnings(unittest.TestCase):
    """A release the skill could not expand must say so — a silent gap looks like a full board."""

    def payload(self, warnings):
        return {"main": {"issues": [], "mrs": {}, "history": [],
                         "meta": {"warnings": warnings}}}

    def test_a_warning_from_the_skill_reaches_the_page(self):
        html = releases.body(self.payload(["Jira no longer knows: Ghost 9.9.9"]))

        self.assertIn("banner warn", html)
        self.assertIn("Ghost 9.9.9", html)

    def test_no_warning_adds_no_banner(self):
        self.assertNotIn("banner warn", releases.body(self.payload([])))

    def test_a_payload_without_meta_still_renders(self):
        html = releases.body({"main": {"issues": [], "mrs": {}}})

        self.assertNotIn("banner warn", html)

class ReleaseFolding(unittest.TestCase):
    """Which releases fold themselves. The rule reads my own tasks, not the release total."""

    def issue(self, key, progress, mine=True, release="R 1.0"):
        return {"key": key, "progress": progress, "mine": mine, "release_name": release,
                "status": "Rejected" if progress == "closed" else "Code review", "summary": ""}

    def test_a_release_where_all_my_tasks_are_closed_is_finished(self):
        items = [self.issue("ABC-1", "closed"), self.issue("ABC-2", "closed")]

        self.assertEqual("every task closed", releases.finished_reason(items))

    def test_one_open_task_of_mine_keeps_the_release_alive(self):
        items = [self.issue("ABC-1", "closed"), self.issue("ABC-2", "review")]

        self.assertEqual("", releases.finished_reason(items))

    def test_the_team_still_working_does_not_keep_it_open_for_me(self):
        """My one rejected ticket ends the release for me even with the team still on it."""
        items = [self.issue("ABC-1", "closed"),
                 self.issue("DEF-9", "review", mine=False),
                 self.issue("DEF-8", "qa", mine=False)]

        self.assertIn("2 tasks still open for the team", releases.finished_reason(items))

    def test_a_release_i_have_no_task_in_is_never_finished(self):
        items = [self.issue("DEF-9", "closed", mine=False)]

        self.assertEqual("", releases.finished_reason(items))

    def test_a_finished_release_is_marked_for_the_browser_to_fold(self):
        payload = {"main": {"mrs": {}, "issues": [
            self.issue("ABC-1", "closed", release="Old 1.0"),
            self.issue("ABC-2", "review", release="Live 2.0"),
        ]}}
        html = releases.body(payload)

        self.assertIn('data-release="Old 1.0" data-finished=', html)
        self.assertIn('data-release="Live 2.0">', html)

    def test_the_bar_counts_what_was_folded(self):
        payload = {"main": {"mrs": {}, "issues": [self.issue("ABC-1", "closed")]}}

        self.assertIn("1 release folded as finished", releases.body(payload))

    def test_every_release_can_be_folded_by_hand(self):
        payload = {"main": {"mrs": {}, "issues": [self.issue("ABC-2", "review")]}}
        html = releases.body(payload)

        self.assertIn("data-release-fold", html)
        self.assertIn('data-fold-all="yes"', html)


class OvertimeInTheRail(unittest.TestCase):
    """The figure closing the rail. It is rendered by the shell, which has no render._safe."""

    def tearDown(self):
        overtime._cache.update(stamp=None, value=None)

        try:
            os.remove(store.path("tempo"))
        except OSError:
            pass

    def seed(self, days):
        store.record_success("tempo", {"year": {"from": "2026-01-01", "days": days}}, 10, now=1000)
        overtime._cache.update(stamp=None, value=None)

    def test_it_shows_the_total_and_the_months_it_came_from(self):
        self.seed([{"day": "2026-09-16", "workday": True, "total_hours": 11},
                   {"day": "2026-08-12", "workday": True, "total_hours": 10}])

        html = layout.sidebar("tempo")

        self.assertIn("Overtime 2026", html)
        self.assertIn("+5 h", html)
        self.assertIn("<span>September</span>", html)
        self.assertIn("<span>August</span>", html)

    def test_with_nothing_to_show_the_block_is_hidden_not_absent(self):
        """A hidden block can be revealed by the first Tempo run; a missing one needs a reload."""
        html = layout.sidebar("")

        self.assertIn("data-overtime-figure", html)
        self.assertIn('data-open="yes" hidden', html)

    def test_the_figure_is_not_a_link(self):
        """Every anchor in this rail is a nav item: styled as one, and closing the drawer."""
        self.seed([{"day": "2026-09-16", "workday": True, "total_hours": 11}])

        figure = layout.sidebar("").split('class="nav-group nav-foot rail-figure"')[1]

        self.assertNotIn("<a ", figure)

    def test_the_rail_hook_is_not_the_day_editor_checkbox(self):
        """repaint() binds fragments, so a selector both answer to made the checkbox the figure."""
        from workhub.render import tempo

        self.assertNotIn("data-overtime-figure", tempo.body(TEMPO))

    def test_a_nonsense_payload_still_leaves_a_usable_page(self):
        store.record_success("tempo", {"year": "garbage"}, 10, now=1000)
        overtime._cache.update(stamp=None, value=None)

        self.assertIn('href="/settings"', layout.sidebar("settings"))

