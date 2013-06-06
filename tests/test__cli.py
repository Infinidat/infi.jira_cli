from infi import unittest
from infi.pyutils.contexts import contextmanager
from infi.jira_cli.jissue import _jissue as jissue
from infi.jira_cli import jira_adapter
from mock import patch
from infi.execute import execute_assert_success


class ListTestCase(unittest.TestCase):
    @unittest.parameters.iterate("key", ["hostdev", "HOSTDEV"])
    def test_simple(self, key):
        self.assertEquals(jissue(["list", key]), 0)

    def test_requires_key(self):
        self.assertEquals(jissue(["list"]), 1)

    def test_jish(self):
        self.assertEquals(jissue(["list"], dict(JISSUE_PROJECT="HOSTDEV")), 0)

    @unittest.parameters.iterate("flag", ["--sort-by=summary", "--reverse", "--assignee=guyr"])
    def test_additional_flags(self, flag):
        self.assertEquals(jissue(["list", "HOSTDEV", flag]), 0)


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
        self.assertEquals(jissue(["search", self.query]), 0)

    @unittest.parameters.iterate("flag", ["--sort-by=summary", "--reverse"])
    def test_additional_flags(self, flag):
        self.assertEquals(jissue(["search", self.query, flag]), 0)


class WorkLogTestCase(unittest.TestCase):
    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["start", issue.key]), 0)
            self.assertEquals(jissue(["stop", issue.key]), 0)

    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["start"], dict(JISSUE_ISSUE=issue.key)), 0)
            self.assertEquals(jissue(["stop"], dict(JISSUE_ISSUE=issue.key)), 0)


class ShowTestCase(unittest.TestCase):
    @unittest.parameters.iterate("key", ["HOSTDEV-767"])
    def test_simple(self, key):
        self.assertEquals(jissue(["show", key]), 0)

    def test_jish(self, key="HOSTDEV-767"):
        self.assertEquals(jissue(["show"], dict(JISSUE_ISSUE=key)), 0)


class ReopenTestCase(unittest.TestCase):
    def test_simple(self):
        with test_issue_context() as issue:
            fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
            jira_adapter.resolve_issue(issue.key, "Not a Bug", fix_version)
            self.assertEquals(jissue(["reopen", issue.key]), 0)

    def test_jish(self):
        with test_issue_context() as issue:
            fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
            jira_adapter.resolve_issue(issue.key, "Not a Bug", fix_version)
            self.assertEquals(jissue(["reopen"], dict(JISSUE_ISSUE=issue.key)), 0)


@contextmanager
def mock_stdout():
    from StringIO import StringIO
    stdout = StringIO()
    with patch("sys.stdout", new=stdout):
        yield stdout


class CreateTestCase(unittest.TestCase):
    def test_jish_and_short(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        with mock_stdout() as stdout:
            key = jissue(["create", "this is a test", "--short"], dict(JISSUE_PROJECT="HOSTDEV",
                                                                       JISSUE_COMPONENT="jissue",
                                                                       JISSUE_VERSION=fix_version))
        self.assertEquals(key, stdout.getvalue().strip())
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)

    def test_simple(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        with mock_stdout() as stdout:
            key = jissue(["create", "this is a test", "HOSTDEV"])
        self.assertIn(key, stdout.getvalue().strip())
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)

    def test_description(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        summary, description = "summary goes here", "description goes here"
        key = jissue(["create", "{}\n{}".format(summary, description), "HOSTDEV"])
        issue = jira_adapter.get_issue(key)
        self.assertEquals(description, issue.fields().description)
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)

    def test_component(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        key = jissue(["create", "this is a test", "--component=Integration Tests", "HOSTDEV"])
        issue = jira_adapter.get_issue(key)
        self.assertEquals(jira_adapter.issue_mappings['Components'](issue), ["Integration Tests"])
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)

    def test_version(self):
        fix_version = jira_adapter.get_next_release_name_in_project("HOSTDEV")
        key = jissue(["create", "this is a test", "--issue-type=Task", "--fix-version=0.16", "HOSTDEV"])
        issue = jira_adapter.get_issue(key)
        self.assertEquals(jira_adapter.issue_mappings['FixVersions'](issue), ["0.16"])
        self.assertEquals(jira_adapter.issue_mappings['Type'](issue), "Task")
        jira_adapter.resolve_issue(key, 'Not a Bug', fix_version)


class CommentTestCase(unittest.TestCase):
    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["comment", "just a comment", issue.key]), 0)
            with mock_stdout() as stdout:
                jissue(["show", issue.key])
            self.assertIn("just a comment", stdout.getvalue())

    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["comment", "just a comment"], dict(JISSUE_ISSUE=issue.key)), 0)
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
    from StringIO import StringIO
    stdout = StringIO()
    with patch("sys.stderr", new=stdout):
        yield stdout


class CommitTestCase(unittest.TestCase):
    def test_simple(self):
        with unstaged_files_context():
            execute_assert_success(["git", "add", "foo"])
            self.assertEquals(jissue(["commit", "just a message", "HOSTDEV-000"]), 0)
            self.assertIn("just a message", execute_assert_success("git log", shell=True).get_stdout())

    def test_jish_and_file(self):
        with unstaged_files_context():
            execute_assert_success(["git", "add", "foo"])
            with open("foo", "w"):
                pass
            self.assertEquals(jissue(["commit", "just a message", "--file=foo"], dict(JISSUE_ISSUE="HOSTDEV-000")), 0)
            self.assertIn("just a message", execute_assert_success("git log", shell=True).get_stdout())

    def test_commit_fails(self):
        with unstaged_files_context():
            with mock_stderr() as stderr:
                self.assertEquals(jissue(["commit", "just a message", "HOSTDEV-000"]), 1)
                self.assertNotEquals(stderr.getvalue(), '')


class ResolveTestCase(unittest.TestCase):
    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["resolve"], dict(JISSUE_ISSUE=issue.key)), 0)
            raise SkipResolve()

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["resolve", issue.key, "--fix-version", "0.16"]), 0)
            raise SkipResolve()

    def test_not_a_bug(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["resolve", issue.key, "--resolve-as=Not a Bug"]), 0)
            raise SkipResolve()


class LinkTestCase(unittest.TestCase):
    def test_jisk(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["link", "relates", "HOSTDEV-767"], dict(JISSUE_ISSUE=issue.key)), 0)

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["link", "relates", "HOSTDEV-767", issue.key]), 0)


class LabelTestCase(unittest.TestCase):
    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["label", "--label=test"], dict(JISSUE_ISSUE=issue.key)), 0)

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["label", "--label=test", "--label=anothe-test", issue.key]), 0)


class AssignTestCase(unittest.TestCase):
    def test_jish(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["assign", "--assignee=guyr"], dict(JISSUE_ISSUE=issue.key)), 0)

    def test_simple(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["assign", "--to-me", issue.key]), 0)

    def test_automatic(self):
        with test_issue_context() as issue:
            self.assertEquals(jissue(["assign", "--automatic", issue.key]), 0)


class InventoryTestCase(unittest.TestCase):
    def test_simple(self):
        self.assertEquals(jissue(["inventory", "HOSTDEV"]), 0)

    def test_jish(self):
        self.assertEquals(jissue(["inventory"], dict(JISSUE_PROJECT="HOSTDEV")), 0)
