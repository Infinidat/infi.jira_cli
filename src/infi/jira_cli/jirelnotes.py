"""jirelnotes
infinidat jira/confluence release-notes command-line tool

Usage:
    jirelnotes show {project} [--include-next-release]
    jirelnotes publish {project} [--include-next-release]
    jirelnotes notify {project} {version}
    jirelnotes fetch

Options:
    show                                 show the generated release notes
    publish                              publish the release notes to the wiki
    fetch                                print the release note from the wiki
    notify                               find linked issues and put comments
    --project=PROJECT                    project key {project_default}
"""


RELEASE_NOTES_TITLE_KEY = 'Release Notes Title'
RELEASE_NOTES_DESCRIPTION_KEY = 'Release Notes Description'


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


def get_issue_details(issue):
    from .jira_adapter import get_custom_fields
    return dict(key=issue.key,
                title=getattr(issue.fields(), get_custom_fields()[RELEASE_NOTES_TITLE_KEY]),
                description=getattr(issue.fields(), get_custom_fields()[RELEASE_NOTES_DESCRIPTION_KEY]))


def is_bug(issue):
    from .jira_adapter import issue_mappings
    return issue_mappings['Type'](issue) == "Bug"


def is_improvement(issue):
    from .jira_adapter import issue_mappings
    return issue_mappings['Type'](issue) == "Improvement"


def is_new_feature(issue):
    from .jira_adapter import issue_mappings
    return issue_mappings['Type'](issue) == "New Feature"


def get_release_notes_contents_for_specfic_version(project, version):
    from .jira_adapter import get_custom_fields, get_jira
    release_date = getattr(version, 'releaseDate', '')
    base_query = "project={} AND fixVersion={!r} AND {!r} IS NOT EMPTY".format(project.key, str(version.name), RELEASE_NOTES_TITLE_KEY)
    known_issues_query = "project={0} AND {1!r} IS NOT EMPTY AND (" \
                         "(fixVersion IN ('known issues') AND status IN (Open, Reopened)) OR " \
                         "(affectedVersion in ({2!r})) OR " \
                         "(labels=known-issue AND status WAS IN (Resolved) ON {3} AND fixVersion NOT IN ({2!r})))"
    known_issues_query = known_issues_query.format(project.key, RELEASE_NOTES_TITLE_KEY,
                                                   str(version.name), release_date or 'now()')
    resolved_issues = list(get_jira().search_issues(base_query))
    known_issues = list(get_jira().search_issues(known_issues_query))
    if resolved_issues or known_issues_query:
        topics = [dict(name="What's new in this release", issues=[get_issue_details(issue) for issue in resolved_issues if is_new_feature(issue)]),
                  dict(name='Improvements', issues=[get_issue_details(issue) for issue in resolved_issues if is_improvement(issue)]),
                  dict(name='Fixed issues', issues=[get_issue_details(issue) for issue in resolved_issues if is_bug(issue)]),
                  dict(name='Known issues', issues=[get_issue_details(issue) for issue in known_issues])]
        return dict(name=version.name, release_date=release_date, topics=topics)
    else:
        return dict()


def should_appear_in_release_notes(release):
    return bool(release) and any(topic['issues'] for topic in release['topics'])


def render_release_notes(project_name, project_version, include_next_release):
    from re import match
    from jinja2 import Template
    from pkg_resources import resource_string
    from .jira_adapter import get_project, get_version, get_jira, issue_mappings, get_custom_fields
    from .jira_adapter import get_next_release_name_in_project

    template = Template(resource_string('infi.jira_cli', 'release_notes.html'))
    project = get_project(project_name)
    real_versions = [version for version in reversed(project.versions) if
                     match(r'[0-9\.]+', version.name) and not version.archived and
                     version.released or (version.name == get_next_release_name_in_project(project_name) if include_next_release else False)]
    releases = [get_release_notes_contents_for_specfic_version(project, version) for version in real_versions]
    exposed_releases = [release for release in releases if should_appear_in_release_notes(release)]
    return template.render(project=project, releases=exposed_releases)


def publish_release_notes(project_name, project_version, include_next_release):
    from .confluence_adapter import update_page_contents, get_release_notes_page_id
    release_notes = render_release_notes(project_name, project_version, include_next_release)
    update_page_contents(get_release_notes_page_id(project_name), release_notes)


def show_release_notes(project_name, project_version, include_next_release):
    print render_release_notes(project_name, project_version, include_next_release)


def fetch_release_notes(project_name):
    from .confluence_adapter import get_page_contents, get_release_notes_page_id
    print get_page_contents(get_release_notes_page_id(project_name))


def notify_related_tickets(project_name, project_version):
    raise NotImplementedError()


def do_work(arguments):
    project_name = arguments['--project']
    project_version = arguments.get('--release')
    if arguments['show']:
        show_release_notes(project_name, project_version, arguments['--include-next-release'])
    elif arguments['publish']:
        publish_release_notes(project_name, project_version, arguments['--include-next-release'])
    elif arguments['fetch']:
        fetch_release_notes(project_name)
    elif arguments['notify']:
        notify_related_tickets(project_name, project_version)


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
