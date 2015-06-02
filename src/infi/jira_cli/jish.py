"""jish
Usage:
    jish project <project> [<component> [<version> | --no-version]]
    jish component <component>
    jish version <version>
    jish workon <issue>
    jish create <issue-type> <details> [--assign-to-me] [--field=<field-name-and-value...>]
    jish deactivate

 Options:
    --help   this screen
"""

from sys import stderr, stdout
from . import jira_adapter
from os import environ


def _get_arguments(argv):
    from .__version__ import __version__
    from docopt import docopt
    from munch import Munch
    arguments = Munch(docopt(__doc__, argv=argv, help=True, version=__version__))
    return arguments


def clear_environment_variables(environment_variables):
    issue_active = bool(environ.get("JISSUE_ISSUE"))
    if not issue_active:
        environment_variables.update(JISSUE_PROJECT="", JISSUE_VERSION="", JISSUE_COMPONENT="")
    environment_variables.update(JISSUE_ISSUE="")


def set_environment_variables_for_issue(arguments, environment_variables):
    issue_key = arguments.get("<issue>") or environ.get("JISSUE_ISSUE")
    try:
        jira_adapter.get_issue(issue_key or "_")
    except jira_adapter.JIRAError:
        print >> stderr, "no such issue", issue_key
        raise SystemExit(1)
    environment_variables.update(JISSUE_ISSUE=issue_key.upper())


def set_environment_variables_for_project(arguments, environment_variables):
    project_key = arguments.get("<project>") or environ.get("JISSUE_PROJECT")
    try:
        project = jira_adapter.get_project(project_key or "_")
    except jira_adapter.JIRAError:
        print >> stderr, "no such project", project_key
        raise SystemExit(1)
    next_version = jira_adapter.get_next_release_name_in_project(project_key)
    project_version = arguments.get("<version>") if not arguments.project else next_version \
                      or (environ.get("JISSUE_VERSION") if not arguments.project else '') \
                      or next_version
    if project_version not in [item.name for item in project.versions] and not arguments.get("--no-version"):
        print >> stderr, "no such version", project_version
        raise SystemExit(1)
    project_component = arguments.get("<component>") or environ.get("JISSUE_COMPONENT")
    if project_component not in [item.name for item in project.components] + [None, '']:
        print >> stderr, "no such component", project_component
        raise SystemExit(1)
    environment_variables.update(JISSUE_PROJECT=project_key.upper())
    if not arguments.get("--no-version"):
        environment_variables.update(JISSUE_VERSION=project_version)
    if project_component:
        environment_variables.update(JISSUE_COMPONENT=project_component)


def set_environment_variables(arguments, environment_variables):
    if arguments.workon:
        return set_environment_variables_for_issue(arguments, environment_variables)
    return set_environment_variables_for_project(arguments, environment_variables)


def _jish(argv):
    from .config import Configuration
    try:
        arguments = _get_arguments(argv)
    except SystemError, e:
        print >> stderr, e
        return 0
    environment_variables = dict()
    if arguments.deactivate:
        clear_environment_variables(environment_variables)
    elif arguments.project or arguments.component or arguments.version or arguments.workon:
        set_environment_variables(arguments, environment_variables)
    elif arguments.create:
        args = (environ['JISSUE_PROJECT'],
                arguments.get("<issue-type>"),
                environ.get('JISSUE_COMPONENT') or None,
                environ.get('JISSUE_VERSION'),
                arguments.get("<details>"))
        kwargs = {'assignee': Configuration.from_file().username if arguments.get("--assign-to-me") else "-1",
                  'additional_fields': [item.split(':=') for item in arguments.get("--field", list())]}
        arguments.workon = True
        arguments['<issue>'] = jira_adapter.create_issue(*args, **kwargs).key
        set_environment_variables(arguments, environment_variables)
    for key, value in environment_variables.iteritems():
        print >> stdout, "export {}={}\n".format(key, value)


def main():
    from sys import argv
    return _jish(argv[1:])
