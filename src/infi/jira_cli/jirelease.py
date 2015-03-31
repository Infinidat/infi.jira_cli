"""jirelease
infinidat jira project command-line tool

Usage:
    jirelease summary [--since-date=SINCE]
    jirelease list {project}
    jirelease release {project} {version}
    jirelease merge {project} {version} <target-version>
    jirelease delay {project} {version} <delta>
    jirelease reschedule {project} {version} <date>
    jirelease create {project} <target-version> [<delta>] [<description>]
    jirelease move {project} {version} (before | after) <target-version>
    jirelease archive {project} <version-regex>
    jirelease unarchive {project} <version-regex>
    jirelease rename {project} {version} <name>
    jirelease describe {project} {version} <description>

Options:
    summary                              list a summary of today's releases
    list                                 list unarchives releases
    release                              mark version as released
    merge                                move issues to target version and delete the merged one
    delay                                move the release date
    reschedule                           set a new release date
    create                               create a new release
    move                                 move a release up or down
    archive                              mark version as archived
    unarchive                            mark version as unarchived
    rename                               change name
    describe                             change description
    --project=PROJECT                    project key {project_default}
    --release=RELEASE                    version string {version_default}
    --since-date=SINCE                   since when [default: today]
"""


def _get_arguments(argv, environ):
    from .__version__ import __version__
    from docopt import docopt
    from munch import Munch
    project_default = "[default: {}]".format(environ["JISSUE_PROJECT"]) if "JISSUE_PROJECT" in environ else ""
    version_default = "[default: {}]".format(environ["JISSUE_VERSION"]) if "JISSUE_VERSION" in environ else ""
    doc_with_defaults = __doc__.format(project_default=project_default, version_default=version_default,
                                       project="[--project=PROJECT]" if project_default else "--project=PROJECT",
                                       version="[--release=RELEASE]" if version_default else "--release=RELEASE")
    arguments = Munch(docopt(doc_with_defaults, argv=argv, help=True, version=__version__))
    if environ.get("JISSUE_PROJECT") and not arguments.get("--project"):
        arguments["--project"] = environ["JISSUE_PROJECT"]
    if environ.get("JISSUE_VERSION") and not arguments.get("--release"):
        arguments["--release"] = environ["JISSUE_VERSION"]
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
        table.add_row([version.name if version.released else version.name + ' **' if getattr(version, 'overdue', False) else version.name + ' *',
                       getattr(version, 'description', ''), getattr(version, 'releaseDate', '')])
    print(table.get_string())


def release_version(project_name, project_version):
    from .jira_adapter import get_version, to_jira_formatted_date
    from json import loads
    from datetime import datetime
    version = get_version(project_name, project_version)
    if version.released:
        raise AssertionError("version already released")
    unresolved_issue_count = loads(version._session.get(version.self + '/unresolvedIssueCount').text).values()[-1]
    if unresolved_issue_count:
        raise AssertionError("version has {} unresovled issues".format(unresolved_issue_count))
    if not version.releaseDate:
        version.update(releaseDate=to_jira_formatted_date(datetime.today()))
    version.update(released=True)


def merge_releases(project_name, project_version, target_version):
    from .jira_adapter import get_version
    version = get_version(project_name, project_version)
    target_version = get_version(project_name, target_version)
    version.delete(target_version.id, target_version.id)


def parse_deltastring(string):
    from datetime import timedelta
    from argparse import ArgumentTypeError
    DELTA_KEYWORD_ARGUMENTS = dict(w="weeks", d="days")
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
    from .jira_adapter import get_version, to_jira_formatted_date, from_jira_formatted_date
    version = get_version(project_name, project_version)
    version.update(releaseDate=release_date if release_date else None)


def create_new_release(project_name, target_version, delta, description):
    from .jira_adapter import clear_cache, get_jira, get_project, from_jira_formatted_date, to_jira_formatted_date
    from pkg_resources import parse_version
    project = get_project(project_name)
    sorted_versions = sorted(project.versions, key=lambda version: parse_version(version.name))
    previous_version = sorted_versions[0]
    for item in sorted_versions:
        if parse_version(item.name) > parse_version(target_version):
            break
        previous_version = item
    if delta and not hasattr(previous_version, 'releaseDate'):
        raise AssertionError("previous version {} has no release date".format(previous_version.name))
    if delta:
        release_date = to_jira_formatted_date(from_jira_formatted_date(previous_version.releaseDate) + parse_deltastring(delta))
    else:
        release_date = None
    get_jira().create_version(target_version, project, releaseDate=release_date, description=description)
    clear_cache(get_project)
    move_release(project_name, target_version, after=True, target_version=previous_version.name)


def move_release(project_name, project_version, after, target_version):
    from .jira_adapter import get_version, get_project, JIRAError
    from json import dumps
    project = get_project(project_name)
    version = get_version(project_name, project_version)
    target_version = get_version(project_name, target_version)
    if not after: # before
        target_version = project.versions[project.versions.index(target_version)-1]
    url = version.self + '/move'
    response = version._session.post(url, headers={'content-type': 'application/json'}, data=dumps(dict(after=target_version.self)))
    if response.status_code != 200:
        raise JIRAError(url=url, status_code=response.status_code, text=response.reason)


def set_archive(project_name, project_version_regex, archived):
    from .jira_adapter import get_project
    from re import match
    for version in get_project(project_name).versions:
        if match(project_version_regex, version.name):
            version.update(archived=archived)


def set_name(project_name, project_version, name):
    from .jira_adapter import get_version
    version = get_version(project_name, project_version)
    version.update(name=name)


def set_description(project_name, project_version, description):
    from .jira_adapter import get_version
    version = get_version(project_name, project_version)
    version.update(description=description)


def datetime_to_date(item):
    from datetime import date
    return date(item.year, item.month, item.day)


def summary(since):
    from .jira_adapter import iter_projects, from_jira_formatted_date, to_jira_formatted_date
    from datetime import date
    from prettytable import PrettyTable

    table = PrettyTable(["Project", "Version", "Description", "Release Date"])
    table.align = 'l'
    today = date.today()
    since_date = today if since == 'today' else datetime_to_date(from_jira_formatted_date(since))

    for project in iter_projects():
        for version in reversed(project.versions):
            if version.archived:
                continue
            release_date_string = getattr(version, 'releaseDate', '')
            if not release_date_string:
                continue
            release_date = datetime_to_date(from_jira_formatted_date(release_date_string))
            if (release_date-since_date).days<0:
                continue
            if (release_date-today).days>0:
                continue

            table.add_row([project.name,
                           version.name if version.released else version.name + ' **' if getattr(version, 'overdue', False) else version.name + ' *',
                           getattr(version, 'description', ''), getattr(version, 'releaseDate', '')])

    print(table.get_string())


def do_work(arguments):
    project_name = arguments['--project']
    project_version = arguments.get('--release')
    if arguments['summary']:
        summary(arguments.get("--since-date"))
    elif arguments['list']:
        pretty_print_project_versions_in_order(project_name)
    elif arguments['release']:
        release_version(project_name, project_version)
    elif arguments['merge']:
        merge_releases(project_name, project_version, arguments['<target-version>'])
    elif arguments['delay']:
        delay_release(project_name, project_version, arguments['<delta>'])
    elif arguments['reschedule']:
        reschedule_release(project_name, project_version, arguments['<date>'])
    elif arguments['create']:
        create_new_release(project_name, arguments['<target-version>'], arguments['<delta>'], arguments['<description>'])
    elif arguments['move']:
        move_release(project_name, project_version, arguments.get('after'), arguments['<target-version>'])
    elif arguments['archive']:
        set_archive(project_name, arguments['<version-regex>'], True)
    elif arguments['unarchive']:
        set_archive(project_name, arguments['<version-regex>'], False)
    elif arguments['rename']:
        set_name(project_name, project_version, arguments['<name>'])
    elif arguments['describe']:
        set_description(project_name, project_version, arguments['<description>'])


def _jiject(argv, environ):
    from sys import stderr
    from copy import deepcopy
    from jira import JIRAError
    from infi.execute import ExecutionError
    from .actions import choose_action
    from docopt import DocoptExit
    try:
        arguments = _get_arguments(argv, dict(deepcopy(environ)))
        return do_work(arguments)
    except DocoptExit, e:
        print >> stderr, e
        return 1
    except AssertionError, e:
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
