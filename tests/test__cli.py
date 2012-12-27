from infi import unittest
from infi import jira_cli
from mock import patch
from os import environ

class TestCase(unittest.TestCase):
    def test__main(self):
        from docopt import DocoptExit
        with self.assertRaises(DocoptExit):
            jira_cli._jissue(list())

    def test__get_arguments(self):
        argument = jira_cli._get_arguments(["list"])

    def test__choose_action(self):
        with patch("infi.jira_cli.actions.list_issues") as list_issues:
            jira_cli._jissue(["list"])
        self.assertTrue(list_issues.called)

    def test__list(self):
        jira_cli._jissue(["list"])

    def test__modifying_options(self):
        key = jira_cli._jissue(["create", environ.get("TEST_PROJECT", "HOSTDEV"), "jissue test", "--issue-type=Task"])
        target = jira_cli._jissue(["create", environ.get("TEST_PROJECT", "HOSTDEV"), "jissue test", "--issue-type=Task"])
        jira_cli._jissue(["show", key])
        jira_cli._jissue(["start", key])
        jira_cli._jissue(["comment", key, "this is a test"])
        jira_cli._jissue(["stop", key])
        jira_cli._jissue(["show", key])
        jira_cli._jissue(["link", key, target])
        jira_cli._jissue(["show", key])
        jira_cli._jissue(["resolve", target, "this is a test"])
        jira_cli._jissue(["resolve", key, "this is a test"])
        jira_cli._jissue(["show", key])

    def test_show__unicode(self):
        jira_cli._jissue(["show", "HIP-555"])

