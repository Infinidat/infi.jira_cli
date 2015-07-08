"""jissue
infinidat jira issue command-line tool

Usage:
    jissue list {project} [--sort-by=<column-name>] [--reverse] [--assignee=<assignee>]
    jissue search [--sort-by=<column-name>] [--reverse] (--filter=<filter> | <query>)
    jissue start {issue}
    jissue stop {issue}
    jissue show {issue}
    jissue reopen {issue}
    jissue create <issue-type> <details> {project} [--component=<component>] [--fix-version=<version>] [--short] [--assign-to-me] [--field=<field-name-and-value...>]
    jissue comment <message> {issue}
    jissue commit [<message>] {issue} [--file=<file>...]
    jissue resolve {issue} [--resolve-as=<resolution>] [--fix-version=<version>]
    jissue link <link-type> <target-issue> {issue}
    jissue label {issue} --label=<label>...
    jissue assign {issue} (--assignee=<assignee> | --automatic | --to-no-one | --to-me)
    jissue inventory {project}
    jissue filters
    jissue config show
    jissue config set <jira_fqdn> <username> <password>

Options:
    list                                list open issues in project/version
    search                              search for issues
    start                               mark work started on issue
    stop                                mark work stopped on issue
    show                                pretty-print issue details
    reopen                              re-open issue
    create                              create new issue
    comment                             add comment to issue
    commit                              do a Git commit with the issue details in the commit message
    resolve                             mark issue as resolved
    link                                create link between issues
    label                               add labels to issue
    assign                              assign issue to user
    inventory                           list components, versions, transisions in project
    filters                             list issue search filters
    config                              get/set jira configuration
    <project>                           project key {project_default}
    <issue>                             issue key {issue_default}
    <details>                           multiline-string, first line is summary, other is description
    <link-type>                         link type string [default: Duplicate]
    <target-issue>                      target issue
    <issue-type>                        issue type string
    --component=<component>             component name {component_default}
    --fix-version=<version>             version string {version_default}
    --file=<file>...                    files/directories to commit
    --resolve-as=<resolution>           resolution string [default: Fixed]
    --sort-by=<column-name>             column to sort by [default: Rank]
    --assignee=<assignee>               jira user name
    --filter=<filter>                   name of a favorite filter
    --field=<field-name-and-value...>   in format name:=value
    --short                             print just the issue key, useful for scripting
    --help                              show this screen
"""


def _get_arguments(argv, environ):
    from .__version__ import __version__
    from docopt import docopt
    from munch import Munch
    project_default = "[default: {}]".format(environ["JISSUE_PROJECT"]) if "JISSUE_PROJECT" in environ else ""
    version_default = "[default: {}]".format(environ["JISSUE_VERSION"]) if "JISSUE_VERSION" in environ else ""
    component_default = "[default: {}]".format(environ["JISSUE_COMPONENT"]) if "JISSUE_COMPONENT" in environ else ""
    issue_default = "[default: {}]".format(environ["JISSUE_ISSUE"]) if "JISSUE_ISSUE" in environ else ""
    doc_with_defaults = __doc__.format(project_default=project_default, version_default=version_default,
                                       component_default=component_default, issue_default=issue_default,
                                       issue="[<issue>]" if issue_default else "<issue>",
                                       project="[<project>]" if project_default else "<project>")
    arguments = Munch(docopt(doc_with_defaults, argv=argv, help=True, version=__version__))
    if environ.get("JISSUE_PROJECT") and not arguments.get("<project>"):
        arguments["<project>"] = environ["JISSUE_PROJECT"]
    if environ.get("JISSUE_VERSION") and not arguments.get("--fix-version"):
        arguments["--fix-version"] = environ["JISSUE_VERSION"]
    if environ.get("JISSUE_COMPONENT") and not arguments.get("<component>"):
        arguments["<component>"] = environ["JISSUE_COMPONENT"]
    if environ.get("JISSUE_ISSUE") and not arguments.get("<issue>"):
        arguments["<issue>"] = environ["JISSUE_ISSUE"]
    return arguments


def exception_handler(func):
    from sys import stderr
    from jira import JIRAError
    from infi.execute import ExecutionError
    from infi.pyutils.decorators import wraps
    from .config import ConfigurationError
    from docopt import DocoptExit

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs) or 0
        except DocoptExit as e:
            print >> stderr, e
            return 1
        except SystemExit as e:
            print >> stderr, e
            return 0
        except JIRAError as e:
            print >> stderr, e
        except ExecutionError as e:
            print >> stderr, e.result.get_stderr()
        except ConfigurationError as e:
            print >> stderr, e.message
        return 1
    return wrapper


@exception_handler
def _jissue(argv, environ=dict()):
    from copy import deepcopy
    from .actions import choose_action

    arguments = _get_arguments(argv, dict(deepcopy(environ)))
    action = choose_action(argv)
    return action(arguments)


def main():
    from os import environ
    from sys import argv
    return _jissue(argv[1:], environ)
