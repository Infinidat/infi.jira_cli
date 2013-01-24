"""jissue
infinidat jira issue command-line tool

Usage:
    jissue list [--sort-by=<column-name>] [--reverse]
    jissue search [--sort-by=<column-name>] [--reverse] <query>
    jissue start <issue>
    jissue stop <issue>
    jissue show <issue>
    jissue create <project> <summary> [--short] [--issue-type=<issue-type>] [--component=<component>]
    jissue comment <issue> <message>
    jissue resolve (<issue> [<message>] | --commit=<commit>) [--resolve-as=<resolution>] [--fix-version=<version>]
    jissue link <issue> <target-issue> [<message>] [--link-type=<link-type>]
    jissue label <issue> <label>...
    jissue assign <issue> (<assignee> | --automatic | --to-no-one | --to-me)
    jissue inventory <project>
    jissue config show
    jissue config set <fqdn> <username> <password>

Options:
    --sort-by=<column-name>      column to sort by [default: Rank]
    --resolve-as=<resolution>    resolution string [default: Fixed]
    --issue-type=<issue-type>    issue type string [default: Bug]
    --link-type=<link-type>      link type string [default: Duplicate]
    --commit=<commit>            deduce issue and message from git commit
    --short                      print just the issue key, useful for scripting
    --help                       show this screen

More Information:
    jissue list                 lists open issues assigned to self
    jissue search               search issues
    jissue start                start progress
    jissue stop                 stop progress
    jissue create               create a new issue
    jissue comment              add a comment to an existing issue
    jissue resolve              resolve an open issue as fixed
    jissue link                 link between two issues
    jissue inventory            show project inventory
    jissue label                add label
"""

__import__("pkg_resources").declare_namespace(__name__)


def _get_arguments(argv):
    from .__version__ import __version__
    from docopt import docopt
    from bunch import Bunch
    arguments = Bunch(docopt(__doc__, argv=argv, help=True, version=__version__))
    return arguments


def _jissue(argv):
    from jira.exceptions import JIRAError
    from .actions import choose_action
    arguments = _get_arguments(argv)
    action = choose_action(argv)
    try:
        return action(arguments)
    except JIRAError, e:
        print(e)
        return 1


def jissue():
    from sys import argv
    return _jissue(argv[1:])
