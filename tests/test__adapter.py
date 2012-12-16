from infi import unittest
from infi.jira_cli import jira_adapter


class TestCase(unittest.TestCase):
    def test__get_jira(self):
        jira = jira_adapter.get_jira()
