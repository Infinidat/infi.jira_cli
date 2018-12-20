from infi import unittest
from infi.pyutils.contexts import contextmanager
from infi.jira_cli.jissue import _jissue as jissue
from infi.jira_cli import jira_adapter
from mock import patch
from infi.execute import execute_assert_success


class ListTestCase(unittest.TestCase):
    @unittest.parameters.iterate("key", ["hostdev", "HOSTDEV"])
    def test_simple(self, key):
        self.assertEqual(jissue(["list", key]), 0)

    def test_requires_key(self):
        self.assertEqual(jissue(["list"]), 1)

    def test_jish(self):
        self.assertEqual(jissue(["list"], dict(JISSUE_PROJECT="HOSTDEV")), 0)

    @unittest.parameters.iterate("flag", ["--sort-by=summary", "--reverse", "--assignee=guyr"])
    def test_additional_flags(self, flag):
        self.assertEqual(jissue(["list", "HOSTDEV", flag]), 0)


class SkipResolve(Exception):
    pass


@contextmanager
def test_issue_context():
    """:yield: jira issue"""
    fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
    issue = jira_adapter.create_issue("HOSTDEV", "Bug", "jissue", fix_version, "issue in jissue unittest")
    skip_resolve = False
    try:
        yield issue
    except SkipResolve:
        skip_resolve = True
    finally:
        if not skip_resolve:
            jira_adapter.resolve_issue(issue.key, 'Not a Bug', fix_version)


class SearchTestCase(unittest.TestCase):
    query = "project=HOSTDEV"

    def test_simple(self):
        self.assertEqual(jissue(["search", self.query]), 0)

    @unittest.parameters.iterate("flag", ["--sort-by=summary", "--reverse"])
    def test_additional_flags(self, flag):
        self.assertEqual(jissue(["search", self.query, flag]), 0)


class WorkLogTestCase(unittest.TestCase):
    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["assign", "--to-me", issue.key]), 0)
            self.assertEqual(jissue(["start", issue.key]), 0)
            self.assertEqual(jissue(["stop", issue.key]), 0)

    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["assign", "--to-me", issue.key]), 0)
            self.assertEqual(jissue(["start"], dict(JISSUE_ISSUE=issue.key)), 0)
            self.assertEqual(jissue(["stop"], dict(JISSUE_ISSUE=issue.key)), 0)


class ShowTestCase(unittest.TestCase):
    @unittest.parameters.iterate("key", ["HOSTDEV-787"])
    def test_simple(self, key):
        self.assertEqual(jissue(["show", key]), 0)

    def test_jish(self, key="HOSTDEV-787"):
        self.assertEqual(jissue(["show"], dict(JISSUE_ISSUE=key)), 0)


class ReopenTestCase(unittest.TestCase):
    def test_simple(self):
        with test_issue_context() as issue:
            fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
            jira_adapter.resolve_issue(issue.key, "Not a Bug", fix_version)
            self.assertEqual(jissue(["reopen", issue.key]), 0)

    def test_jish(self):
        with test_issue_context() as issue:
            fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
            jira_adapter.resolve_issue(issue.key, "Not a Bug", fix_version)
            self.assertEqual(jissue(["reopen"], dict(JISSUE_ISSUE=issue.key)), 0)


@contextmanager
def mock_stdout():
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
    stdout = StringIO()
    with patch("sys.stdout", new=stdout):
        yield stdout


class CreateTestCase(unittest.TestCase):
    def _create(self, args, environ=dict()):
        with mock_stdout() as stdout:
            jissue(args + ["--short"], environ)
        return stdout.getvalue().strip()

    def test_description(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        summary, description = "summary goes here", "description goes here"
        key = self._create(["create", "bug", "{}\n{}".format(summary, description), "HOSTDEV"])
        issue = jira_adapter.get_issue(key)
        self.assertEquals(description, issue.fields().description)
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)

    def test_component(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        key = self._create(["create", "Bug", "this is a test", "--component=integration-tests", "HOSTDEV"])
        issue = jira_adapter.get_issue(key)
        self.assertEquals(jira_adapter.issue_mappings['Components'](issue), ["integration-tests"])
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)

    def test_component__jish(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        key = self._create(["create", "Bug", "this is a test"], dict(JISSUE_COMPONENT="integration-tests",
                                                                     JISSUE_PROJECT="HOSTDEV"))
        issue = jira_adapter.get_issue(key)
        self.assertEquals(jira_adapter.issue_mappings['Components'](issue), ["integration-tests"])
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)

    def test_version(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        key = self._create(["create", "task", "this is a test", "--fix-version=0.16", "HOSTDEV"])
        issue = jira_adapter.get_issue(key)
        self.assertEquals(jira_adapter.issue_mappings['FixVersions'](issue), ["0.16"])
        self.assertEquals(jira_adapter.issue_mappings['Type'](issue), "Task")
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)


class CommentTestCase(unittest.TestCase):
    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["comment", "just a comment", issue.key]), 0)
            with mock_stdout() as stdout:
                jissue(["show", issue.key])
            self.assertIn("just a comment", stdout.getvalue())

    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["comment", "just a comment"], dict(JISSUE_ISSUE=issue.key)), 0)
            with mock_stdout() as stdout:
                jissue(["show", issue.key])
            self.assertIn("just a comment", stdout.getvalue())


@contextmanager
def unstaged_files_context():
    from tempfile import mkdtemp
    from os import path, chdir
    curdir = path.abspath(path.curdir)
    tempdir = mkdtemp()
    chdir(tempdir)
    execute_assert_success(["git", "init", "."])
    with open("foo", "w") as fd:
        fd.write("bar")
    try:
        yield
    finally:
        chdir(curdir)


@contextmanager
def mock_stderr():
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
    stdout = StringIO()
    with patch("sys.stderr", new=stdout):
        yield stdout


class CommitTestCase(unittest.TestCase):
    def test_simple(self):
        with unstaged_files_context():
            execute_assert_success(["git", "add", "foo"])
            self.assertEqual(jissue(["commit", "just a message", "HOSTDEV-955"]), 0)
            self.assertIn("just a message", execute_assert_success("git log", shell=True).get_stdout().decode("ascii"))

    def test_jish_and_file(self):
        with unstaged_files_context():
            execute_assert_success(["git", "add", "foo"])
            with open("foo", "w"):
                pass
            self.assertEqual(jissue(["commit", "just a message", "--file=foo"], dict(JISSUE_ISSUE="HOSTDEV-955")), 0)
            self.assertIn("just a message", execute_assert_success("git log", shell=True).get_stdout().decode("ascii"))

    def test_commit_fails(self):
        with unstaged_files_context():
            with mock_stderr() as stderr:
                self.assertEqual(jissue(["commit", "just a message", "HOSTDEV-955"]), 1)


class ResolveTestCase(unittest.TestCase):
    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["resolve"], dict(JISSUE_ISSUE=issue.key)), 0)
            raise SkipResolve()

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["resolve", issue.key, "--fix-version", "0.16"]), 0)
            raise SkipResolve()

    def test_not_a_bug(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["resolve", issue.key, "--resolve-as=Not a Bug"]), 0)
            raise SkipResolve()


class LinkTestCase(unittest.TestCase):
    def test_jisk(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["link", "relates", "HOSTDEV-787"], dict(JISSUE_ISSUE=issue.key)), 0)

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["link", "relates", "HOSTDEV-787", issue.key]), 0)


class LabelTestCase(unittest.TestCase):
    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["label", "--label=test"], dict(JISSUE_ISSUE=issue.key)), 0)

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["label", "--label=test", "--label=anothe-test", issue.key]), 0)


class AssignTestCase(unittest.TestCase):
    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["assign", "--assignee=guyr"], dict(JISSUE_ISSUE=issue.key)), 0)

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["assign", "--to-me", issue.key]), 0)

    def test_automatic(self):
        with test_issue_context() as issue:
            self.assertEqual(jissue(["assign", "--automatic", issue.key]), 0)


class InventoryTestCase(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(jissue(["inventory", "HOSTDEV"]), 0)

    def test_jish(self):
        self.assertEqual(jissue(["inventory"], dict(JISSUE_PROJECT="HOSTDEV")), 0)
