"""jirelease
infinidat jira/confluence release-notes command-line tool

Usage:
    jirelease show {project} {version}
    jirelease add-to-page <page-id> {project} {version}
    jirelease publish <page-id> {project} {version}
    jirelease fetch <page-id>

Options:
    show                                 show the generated release notes
    --project=PROJECT                    project key {project_default}
    --release=RELEASE                    version string {version_default}
"""


def _get_arguments(argv, environ):
    from .__version__ import __version__
    from docopt import docopt
    from munch import Munch
    project_default = "[default: {}]".format(environ["JISSUE_PROJECT"]) if "JISSUE_PROJECT" in environ else ""
    version_default = "[default: {}]".format(environ["JISSUE_VERSION"]) if "JISSUE_VERSION" in environ else ""
    doc_with_defaults = __doc__.format(project_default=project_default, version_default=version_default,
                                       project="[--project=PROJECT]" if project_default else "--project=PROEJCT",
                                       version="[--release=RELEASE]" if version_default else "--release=RELEASE")
    arguments = Munch(docopt(doc_with_defaults, argv=argv, help=True, version=__version__))
    if environ.get("JISSUE_PROJECT") and not arguments.get("--project"):
        arguments["--project"] = environ["JISSUE_PROJECT"]
    if environ.get("JISSUE_VERSION") and not arguments.get("--release"):
        arguments["--release"] = environ["JISSUE_VERSION"]
    return arguments


def render_release_notes(project_name, project_version):
    from jinja2 import Template
    from pkg_resources import resource_string
    from .jira_adapter import get_project, get_version, get_jira, issue_mappings

    template = Template(resource_string('infi.jira_cli', 'release_notes.html'))
    issue_list = list(get_jira().search_issues("project={!r} and fixVersion={!r}".format(project_name, project_version)))
    issues = dict()
    for issue in issue_list:
        issues.setdefault(issue_mappings['Type'](issue), list()).append(dict(key=issue.key, summary=issue_mappings['Summary'](issue)))
    return template.render(project=get_project(project_name), release=get_version(project_name, project_version),
                           issues=issues)


def add_to_release_notes(project_name, project_version, page_id):
    from .confluence_adapter import get_confluence
    release_notes = render_release_notes(project_name, project_version)
    confluence = get_confluence()
    page = confluence.get('content/{}?expand=body.view,version.number'.format(page_id))
    data = dict(version=dict(number=page['version']['number']+1),
                id=page['id'], title=page['title'], type='page',
                body=dict(representation='storage', storage=dict(value=release_notes+page['body']['view']['value'])))
    confluence.put('content/%s' % page_id, data=data)


def publish_release_notes(project_name, project_version, page_id):
    from .confluence_adapter import get_confluence
    release_notes = render_release_notes(project_name, project_version)
    confluence = get_confluence()
    page = confluence.get('content/{}?expand=body.view,version.number'.format(page_id))
    data = dict(version=dict(number=page['version']['number']+1),
                id=page['id'], title=page['title'], type='page',
                body=dict(representation='storage', storage=dict(value=release_notes)))
    confluence.put('content/%s' % page_id, data=data)


def show_release_notes(project_name, project_version):
    print render_release_notes(project_name, project_version)


def fetch_page(page_id):
    from .confluence_adapter import get_confluence
    confluence = get_confluence()
    page = confluence.get('content/{}?expand=body.view,version.number'.format(page_id))
    print page['body']['view']['value']


def do_work(arguments):
    project_name = arguments['--project']
    project_version = arguments.get('--release')
    if arguments['show']:
        show_release_notes(project_name, project_version)
    elif arguments['add-to-page']:
        add_to_release_notes(project_name, project_version, arguments['<page-id>'])
    elif arguments['publish']:
        publish_release_notes(project_name, project_version, arguments['<page-id>'])
    elif arguments['fetch']:
        fetch_page(arguments['<page-id>'])

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
