"""jirelnotes
infinidat jira/confluence release-notes command-line tool

Usage:
    jirelnotes show {project} [--include-next-release]
    jirelnotes publish {project} [--include-next-release]
    jirelnotes notify {project} {version} [<other-versions-included-in-this-releases>...] [--dry-run]
    jirelnotes fetch {project}

Options:
    show                                 show the generated release notes
    publish                              publish the release notes to the wiki
    fetch                                print the release note from the wiki
    notify                               find linked issues and put comments
    --project=PROJECT                    project key {project_default}
"""

RELEASE_NOTES_TITLE_KEY = 'Release Notes Title'
RELEASE_NOTES_DESCRIPTION_KEY = 'Release Notes Description'
NOTIFICATION_MESSAGE = """{{ project.name }} v{{ version }} has been released and now available for download.
{% if other_versions %}
This release supersedes the following unreleased versions:
{%- for version in other_versions %}
* {{ version }}
{%- endfor %}
{%- endif %}
{% if resolved_issues %}
This release solves the following related issues:
{%- for issue in resolved_issues %}
* {{ issue.key }}: {{ issue_mappings.Summary(issue) }}
{%- endfor %}
{%- endif %}
{% if unresolved_issues %}
Still, there are more related issues that are still open:
{%- for issue in unresolved_issues %}
* {{ issue.key }}: {{ issue_mappings.Summary(issue) }}
{%- endfor %}
{%- else %}
All related issues are now resolved.
{%- endif %}
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



def render_release_notes(project_key, project_version, include_next_release, page_id, header_id, footer_id):
    from re import match
    from jinja2 import Template
    from pkg_resources import resource_string
    from .jira_adapter import get_project, get_version, get_jira, issue_mappings, get_custom_fields
    from .jira_adapter import get_next_release_name_in_project
    from .confluence_adapter import iter_attachments, get_page_contents
    template = Template(resource_string('infi.jira_cli', 'release_notes.html'))
    project = get_project(project_key)
    real_versions = [version for version in reversed(project.versions) if
                     match(r'[0-9\.]+', version.name) and not version.archived and
                     version.released or (version.name == get_next_release_name_in_project(project_key) if include_next_release else False)]
    releases = [get_release_notes_contents_for_specfic_version(project, version) for version in real_versions]
    attachments = list(iter_attachments(page_id))
    exposed_releases = [release for release in releases if should_appear_in_release_notes(release)]
    return template.render(project=project, releases=exposed_releases, page_id=page_id, attachments=attachments,
                           header=get_page_contents(header_id) if header_id else None,
                           footer=get_page_contents(footer_id) if footer_id else None)


def get_release_notes(project_key, project_version, include_next_release):
    from .confluence_adapter import get_release_notes_page_id
    from .confluence_adapter import get_release_notes_header_page_id, get_release_notes_footer_page_id
    page_id = get_release_notes_page_id(project_key)
    header_id = get_release_notes_header_page_id(project_key)
    footer_id = get_release_notes_footer_page_id(project_key)
    release_notes = render_release_notes(project_key, project_version, include_next_release, page_id, header_id, footer_id)
    return release_notes, page_id


def publish_release_notes(project_key, project_version, include_next_release):
    from .confluence_adapter import update_page_contents
    release_notes, page_id = get_release_notes(project_key, project_version, include_next_release)
    update_page_contents(page_id, release_notes)


def show_release_notes(project_key, project_version, include_next_release):
    release_notes, page_id = get_release_notes(project_key, project_version, include_next_release)
    print release_notes


def fetch_release_notes(project_key):
    from .confluence_adapter import get_page_contents, get_release_notes_page_id
    print get_page_contents(get_release_notes_page_id(project_key))


def notify_related_tickets(project_key, project_version, other_versions, dry_run):
    def _build_jira_query_string():
        from pkg_resources import parse_version
        if other_versions:
            versions.extend(sorted(set(other_versions + [project_version]), key=lambda version: parse_version(version)))
            fix_version_string = 'fixVersion in ({})'.format(', '.join([repr(version) for version in versions]))
        else:
            fix_version_string = 'fixVersion={!r}'.format(project_version)
        return "project={} AND {} AND resolution=Fixed".format(project_key, fix_version_string)

    def _iter_related_tickets(issue):
        for link in issue_mappings.IssueLinks(issue):
            if not link.type.name in (u'Originates', u'Clones', u'Cloners', u'Relates', 'Supersede', 'Duplicate'):
                continue
            related_issue = getattr(link, 'inwardIssue', getattr(link, 'outwardIssue', None))
            if related_issue.key.startswith(project_key.upper()):
                continue
            yield related_issue

    def find_issues_in_other_projects_that_are_pending_on_this_release():
        related_tickets = {}
        for issue in search_issues(_build_jira_query_string()):
            for related_ticket in _iter_related_tickets(issue):
                related_tickets.setdefault(get_issue(related_ticket.key), list()).append(issue)
        return related_tickets

    def _iter_related_remaining_open_issues(related_ticket):
        for link in issue_mappings.IssueLinks(related_ticket):
            if not hasattr(link, 'outwardIssue'):
                continue
            if not issue_mappings.Status(link.outwardIssue) in (u'Open', 'Reopened'):
                continue
            yield link.outwardIssue

    def _build_comment(resolved_issues, unresolved_issues):
        from jinja2 import Template
        sort_issues = lambda issues: sorted(issues, key=lambda issue: issue.key)
        notification_template = Template(NOTIFICATION_MESSAGE.strip())
        return notification_template.render(project=project,
                                            version=project_version,
                                            other_versions=versions[:-1],
                                            resolved_issues=sort_issues(resolved_issues),
                                            unresolved_issues=sort_issues(unresolved_issues),
                                            issue_mappings=issue_mappings)

    from .jira_adapter import search_issues, issue_mappings, comment_on_issue, get_project, get_issue
    project = get_project(project_key)
    versions = []
    related_tickets = find_issues_in_other_projects_that_are_pending_on_this_release()
    for related_ticket, resolved_issues in sorted(related_tickets.items(), key=lambda item: item[0].key):
        unresolved_issues = list(_iter_related_remaining_open_issues(related_ticket))
        comment = _build_comment(resolved_issues, unresolved_issues)
        comment = "".join(i for i in comment if ord(i)<128)
        if dry_run:
            print "<--- COMMENT ON {0} STARTS HERE --->\n{1}\n<--- COMMENT ON {0} ENDS HERE ----->".format(related_ticket.key, comment)
        else:
            print 'commenting on %s' % related_ticket.key
            comment_on_issue(related_ticket.key, comment)


def do_work(arguments):
    project_key = arguments['--project']
    project_version = arguments.get('--release')
    if arguments['show']:
        show_release_notes(project_key, project_version, arguments['--include-next-release'])
    elif arguments['publish']:
        publish_release_notes(project_key, project_version, arguments['--include-next-release'])
    elif arguments['fetch']:
        fetch_release_notes(project_key)
    elif arguments['notify']:
        other_versions = arguments.get('<other-versions-included-in-this-releases>', list())
        notify_related_tickets(project_key, project_version, other_versions, arguments['--dry-run'])


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
