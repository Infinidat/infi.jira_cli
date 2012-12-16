"""jissue
infinidat jira issue command-line tool

Usage:
    jissue list [--sort-by=<column-name>] [--reverse]
    jissue start <issue>
    jissue stop <issue>
    jissue show <issue>
    jissue create <project> <summary> [--issue-type=<issue-type>] [--component=<component>]
    jissue comment <issue> <message>
    jissue resolve <issue> [<message>] [--resolve-as=<resolution>] [--fix-version=<version>]
    jissue link <issue> <target-issue> [<message>] [--link-type=<link-type>]
    jissue config show
    jissue config set <fqdn> <username> <password>

Options:
    --sort-by=<column-name>      column to sort by [default: Rank]
    --resolve-as=<resolution>    resolution string [default: Fixed]
    --issue-type=<issue-type>    issue type string [default: Bug]
    --link-type=<link-type>      link type string [default: Duplicate]
    --help                       show this screen

More Information:
    jissue list                 lists open issues assigned to selffg
    jissue start                start progress
    jissue stop                 stop progress
    jissue create               create a new issue
    jissue comment              add a comment to an existing issue
    jissue resolve              resolve an open issue as fixed
    jissue link                 link between two issues
"""

__import__("pkg_resources").declare_namespace(__name__)


def _get_arguments(argv):
    from .__version__ import __version__
    from docopt import docopt
    from bunch import Bunch
    arguments = Bunch(docopt(__doc__, argv=argv, help=True, version=__version__))
    return arguments


def _jissue(argv):
    from .actions import choose_action
    arguments = _get_arguments(argv)
    action = choose_action(argv)
    return action(arguments)

def jissue():
    from sys import argv
    _jissue(argv[1:])
    return 0
