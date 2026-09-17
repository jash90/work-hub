"""Settings: parsing `.env`, saving it, and never handing a stored secret back."""
import os
import unittest

from . import context  # noqa: F401
from workhub import config, runner


class EnvFile(unittest.TestCase):
    def setUp(self):
        self.addCleanup(self.clear)
        self.clear()

    def clear(self):
        config._cache.update(stamp=None, values={})

        if os.path.exists(config.ENV_PATH):
            os.unlink(config.ENV_PATH)

    def write(self, text):
        with open(config.ENV_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)

        config._cache.update(stamp=None, values={})

    def test_a_missing_file_is_not_an_error(self):
        self.assertEqual({}, config.load())

    def test_comments_and_blank_lines_are_skipped(self):
        self.write("# a comment\n\nJIRA_TOKEN=abc\n")

        self.assertEqual({"JIRA_TOKEN": "abc"}, config.load())

    def test_quotes_are_stripped_and_an_equals_sign_survives(self):
        self.write('JIRA_BASE_URL="https://j.example.com"\nGITLAB_TOKEN=a=b=c\n')
        values = config.load()

        self.assertEqual("https://j.example.com", values["JIRA_BASE_URL"])
        self.assertEqual("a=b=c", values["GITLAB_TOKEN"])

    def test_a_saved_file_reads_back(self):
        config.save({"JIRA_TOKEN": "a-secret", "TEMPO_USER": "first.last"})

        self.assertEqual("a-secret", config.load()["JIRA_TOKEN"])
        self.assertEqual("first.last", config.load()["TEMPO_USER"])

    def test_the_file_is_not_readable_by_anyone_else(self):
        config.save({"JIRA_TOKEN": "a-secret"})

        self.assertEqual(0o600, os.stat(config.ENV_PATH).st_mode & 0o777)

    def test_an_unknown_key_is_refused_rather_than_stored(self):
        with self.assertRaises(KeyError):
            config.save({"RM_RF": "no"})

    def test_an_absent_key_keeps_its_value_but_an_empty_one_clears_it(self):
        """The form cannot show a stored token, so silence must not mean deletion."""
        config.save({"JIRA_TOKEN": "a-secret", "GITLAB_TOKEN": "second"})
        config.save({"TEMPO_USER": "someone"})

        self.assertEqual("a-secret", config.load()["JIRA_TOKEN"])

        config.save({"JIRA_TOKEN": ""})

        self.assertNotIn("JIRA_TOKEN", config.load())
        self.assertEqual("second", config.load()["GITLAB_TOKEN"])

    def test_a_rewritten_file_is_read_again(self):
        self.write("TEMPO_USER=first\n")
        self.assertEqual("first", config.load()["TEMPO_USER"])

        self.write("TEMPO_USER=second\n")
        self.assertEqual("second", config.load()["TEMPO_USER"])


class Describe(unittest.TestCase):
    def setUp(self):
        self.addCleanup(self.clear)
        self.clear()

    def clear(self):
        config._cache.update(stamp=None, values={})

        if os.path.exists(config.ENV_PATH):
            os.unlink(config.ENV_PATH)

    def item(self, key):
        return next(i for i in config.describe() if i["key"] == key)

    def test_a_secret_is_never_handed_back(self):
        config.save({"JIRA_TOKEN": "very-secret-token-3f0a"})
        item = self.item("JIRA_TOKEN")

        self.assertNotIn("very-secret-token", repr(config.describe()))
        self.assertEqual("…3f0a", item["hint"])
        self.assertTrue(item["set"])

    def test_a_short_secret_leaks_nothing_either(self):
        config.save({"JIRA_TOKEN": "abc"})

        self.assertEqual("…", self.item("JIRA_TOKEN")["hint"])

    def test_a_plain_setting_is_shown_because_it_is_not_a_secret(self):
        config.save({"TEMPO_USER": "first.last"})

        self.assertEqual("first.last", self.item("TEMPO_USER")["hint"])

    def test_an_unset_setting_reports_no_source(self):
        self.assertEqual("", self.item("CONFLUENCE_TOKEN")["source"])
        self.assertFalse(self.item("CONFLUENCE_TOKEN")["set"])

    def test_a_value_in_the_env_file_reports_that_source(self):
        config.save({"GITLAB_TOKEN": "x"})

        self.assertEqual(".env", self.item("GITLAB_TOKEN")["source"])

    def test_a_token_file_is_found_even_without_an_env_entry(self):
        os.makedirs(config.SECRETS_DIR, exist_ok=True)
        path = os.path.join(config.SECRETS_DIR, config.SECRET_FILES["CONFLUENCE_TOKEN"])

        with open(path, "w") as handle:
            handle.write("z-pliku\n")

        self.addCleanup(os.unlink, path)

        self.assertEqual("file", self.item("CONFLUENCE_TOKEN")["source"])
        self.assertFalse(self.item("CONFLUENCE_TOKEN")["set"])


class SecretFiles(unittest.TestCase):
    """tempo-fill reads a file and ignores the environment, so a token must land there too."""

    def test_a_token_is_mirrored_with_no_access_for_anyone_else(self):
        written = config.sync_secret_files({"JIRA_TOKEN": "a-secret"})
        path = os.path.join(config.SECRETS_DIR, "jira-token")
        self.addCleanup(os.unlink, path)

        with open(path) as handle:
            self.assertEqual("a-secret", handle.read().strip())

        self.assertIn("jira-token", written)
        self.assertEqual(0o600, os.stat(path).st_mode & 0o777)

    def test_nothing_is_written_for_a_setting_that_has_no_value(self):
        self.assertEqual([], config.sync_secret_files({"JIRA_TOKEN": "  "}))

    def test_it_writes_inside_the_sandbox_not_the_real_secrets_directory(self):
        """The guard that keeps this suite from overwriting the user's own token."""
        self.assertNotIn(os.path.expanduser("~/.claude/.secrets"), config.SECRETS_DIR)


class SubprocessEnvironment(unittest.TestCase):
    def setUp(self):
        self.addCleanup(self.clear)
        self.clear()

    def clear(self):
        config._cache.update(stamp=None, values={})

        if os.path.exists(config.ENV_PATH):
            os.unlink(config.ENV_PATH)

    def test_the_env_file_covers_the_process_environment(self):
        os.environ["GITLAB_TOKEN"] = "from-the-environment"
        self.addCleanup(os.environ.pop, "GITLAB_TOKEN", None)
        config.save({"GITLAB_TOKEN": "from-the-file"})

        self.assertEqual("from-the-file", runner._env()["GITLAB_TOKEN"])

    def test_the_process_environment_is_never_mutated(self):
        config.save({"TEMPO_USER": "someone"})
        runner._env()

        self.assertIsNone(os.environ.get("TEMPO_USER"))

    def test_the_path_still_wins_because_glab_must_be_found(self):
        config.save({"JIRA_TOKEN": "x"})

        self.assertEqual(runner.PATH, runner._env()["PATH"])


class Example(unittest.TestCase):
    def test_every_setting_appears_with_no_value_behind_it(self):
        text = config.example()

        for setting in config.SETTINGS:
            self.assertIn(setting.key, text)

        for line in text.splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                self.assertEqual(config.BY_KEY[key].placeholder, value)


if __name__ == "__main__":
    unittest.main()
