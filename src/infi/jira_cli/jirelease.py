"""jirelease
infinidat jira project command-line tool

Usage:
    jirelease list {project}
    jirelease release {project} {version} [--move-unresolved-issues-to-next-version | --move-unresolved-issues-to-specific-version=<next-version>]
    jirelease merge {project} {version} <target-version>
    jirelease delay {project} {version} <delta>
    jirelease reschedule {project} {version} <date>
    jirelease create {project} {version} <date>
    jirelease move {project} {version} <direction> <count>
    jirelease reorganize {project} {version}
    jirelease archive <project> <version-regex>
    jirelease unarchive <project> <version-regex>

Options:
    <project>                    project key {project_default}
    <version>                    version string {version_default}

"""


def _get_arguments(argv, environ):
    from .__version__ import __version__
    from docopt import docopt
    from munch import Munch
    project_default = "[default: {}]".format(environ["JISSUE_PROJECT"]) if "JISSUE_PROJECT" in environ else ""
    version_default = "[default: {}]".format(environ["JISSUE_VERSION"]) if "JISSUE_VERSION" in environ else ""
    doc_with_defaults = __doc__.format(project_default=project_default, version_default=version_default,
                                       project="[<project>]" if project_default else "<project>",
                                       version="[<version>]" if version_default else "<version>")
    arguments = Munch(docopt(doc_with_defaults, argv=argv, help=True, version=__version__))
    if environ.get("JISSUE_PROJECT") and not arguments.get("<project>"):
        arguments["<project>"] = environ["JISSUE_PROJECT"]
    if environ.get("JISSUE_VERSION") and not arguments.get("--fix-version"):
        arguments["--fix-version"] = environ["JISSUE_VERSION"]
    return arguments


def pretty_print_project_versions_in_order(project_name):
    from .jira_adapter import get_project, from_jira_formatted_datetime
    from prettytable import PrettyTable
    project = get_project(project_name)
    table = PrettyTable(["Name", "Description", "Release Date"])
    table.align = 'l'

    for version in reversed(project.versions):
        if version.archived:
            continue
        table.add_row([version.name, getattr(version, 'description', ''), getattr(version, 'releaseDate', '')])
    print(table.get_string())


def release_version(project_name, project_version, move_to_next_version, move_to_specific_version):
    raise NotImplementedError()


def merge_releases(project_name, project_version, target_version):
    raise NotImplementedError()


def parse_deltastring(string):
    from datetime import timedelta
    from argparse import ArgumentTypeError
    keyword_argument = DELTA_KEYWORD_ARGUMENTS.get(string[-1] if string else "", "seconds")
    stripped_string = string.strip(''.join(DELTA_KEYWORD_ARGUMENTS.keys()))
    try:
        return timedelta(**{keyword_argument: abs(int(stripped_string))})
    except (ValueError, TypeError), msg:
        raise ValueError("Invalid delta string: {!r}".format(string))


def delay_release(project_name, project_version, delta):
    from .jira_adapter import get_version, to_jira_formatted_date, from_jira_formatted_date
    version = get_version(project_name, project_version)
    new_release_date = from_jira_formatted_date(version.releaseDate) + parse_deltastring(delta)
    version.update(releaseDate=to_jira_formatted_date(new_release_date))


def reschedule_release(project_name, project_version, release_date):
    raise NotImplementedError()


def create_new_release(project_name, project_version, release_date):
    raise NotImplementedError()


def move_release(project_name, project_version, shift):
    raise NotImplementedError()


def reorganize_project(project_name, specific_versions):
    raise NotImplementedError()


def set_archive(project_name, project_version_regex, archived):
    from .jira_adapter import get_project
    from re import match
    for version in get_project(project_name).versions:
        if match(project_version_regex, version.name):
            version.update(archived=archived)


def do_work(arguments):
    project_name = arguments['<project>']
    project_version = arguments.get('<version>')
    if arguments['list']:
        pretty_print_project_versions_in_order(project_name)
    elif arguments['release']:
        release_version(project_name, project_version,
                        arguments.get('--move-unresolved-issues-to-next-version'),
                        arguments.get('--move-unresolved-issues-to-specific-version'))
    elif arguments['merge']:
        merge_releases(project_name, project_version, arguments['<target-version>'])
    elif arguments['delay']:
        delay_release(project_name, project_version, delta=arguments['<delta>'])
    elif arguments['reschedule']:
        reschedule_release(project_name, project_version, release_date=arguments['<date>'])
    elif arguments['create']:
        create_new_release(project_name, project_version, release_date=arguments['<date>'])
    elif arguments['move']:
        direction = arguments['<direction>']
        count = int(arguments['count'])
        assert direction in ('up', 'down')
        move_release(project_name, project_version, count if direction == 'up' else -1*count)
    elif arguments['reorganize']:
        reorganize_project(project_name, specific_versions=[project_version] if project_version else [])
    elif arguments['archive']:
        set_archive(project_name, arguments['<version-regex>'], True)
    elif arguments['unarchive']:
        set_archive(project_name, arguments['<version-regex>'], False)


def _jiject(argv, environ):
    from sys import stderr
    from copy import deepcopy
    from jira.exceptions import JIRAError
    from infi.execute import ExecutionError
    from .actions import choose_action
    from docopt import DocoptExit
    try:
        arguments = _get_arguments(argv, dict(deepcopy(environ)))
        return do_work(arguments)
    except DocoptExit, e:
        print >> stderr, e
        return 1
    except SystemExit, e:
        print >> stderr, e
        return 0
    except JIRAError, e:
        print >> stderr, e
    except ExecutionError, e:
        print >> stderr, e.result.get_stderr()
    return 1


def main():
    from os import environ
    from sys import argv
    return _jiject(argv[1:], environ)
