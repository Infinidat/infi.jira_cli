from infi.pyutils.lazy import cached_function, clear_cache
from jira import JIRAError
from munch import Munch
from logging import getLogger
from functools import partial
from .config import Configuration
from .custom_field_editor import GET_URI, get_jira_url
import requests
from infi.pyutils.lazy import cached_function
from .config import Configuration
from .credential_store import JIRACredentialsStore
from requests.auth import HTTPBasicAuth


logger = getLogger(__name__)


CURRENT_USER = "currentUser()"
ASSIGNED_ISSUES = "{}assignee = {} AND resolution = unresolved ORDER BY priority DESC, created ASC"


@cached_function
def get_auth(fqdn):
    config = Configuration.from_file()
    credential_store = JIRACredentialsStore()
    credentials = credential_store.get_credentials(fqdn)
    return HTTPBasicAuth(credentials.get_username(), credentials.get_password())


@cached_function
def get_headers():
    return {'Accept': 'application/json'}


@cached_function
def get_jira():
    from jira import JIRA as _JIRA

    class JIRA(_JIRA):
        def __del__(self):
            # workaround for silencing the exception thrown upon exit to stderr
            # Exception AttributeError: "'NoneType' object has no attribute 'version_info'" in <bound method JIRA.__del__ of <jira.client.JIRA object at 0x10e46a250>> ignored
            pass

    config = Configuration.from_file()
    options = dict(server="https://{0}".format(config.jira_fqdn))
    basic_auth = get_auth(config.jira_fqdn)
    return JIRA(options, basic_auth=(basic_auth.username, basic_auth.password))


@cached_function
def get_custom_fields():
    return {item['name']: item['id'] for item in get_jira().fields() if item['custom']}


@cached_function
def get_custom_fields_schema():
    return {item['name']: item['schema']['custom'] for item in get_jira().fields() if item['custom']}


@cached_function
def get_issues__assigned_to_user(user, project=None):
    return get_jira().search_issues(ASSIGNED_ISSUES.format("project={} AND ".format(project) if project else '', user))


@cached_function
def get_issues__assigned_to_me(project=None):
    return get_issues__assigned_to_user(CURRENT_USER, project)


def add_labels_to_issue(key, labels):
    issue = get_issue(key)
    labels = set.union(set([str(label) for label in labels]), set(issue.fields().labels))
    issue.update(labels=[dict(add=label) for label in labels])


def assign_issue(key, assignee):
    get_jira().assign_issue(key, assignee)


def from_jira_formatted_datetime(formatted_string):
    # http://stackoverflow.com/questions/127803/how-to-parse-iso-formatted-date-in-python
    import re
    import datetime
    return datetime.datetime(*list(map(int, re.split('[^\d]', formatted_string)[:-1])))


def from_jira_formatted_date(formatted_string):
    return from_jira_formatted_datetime(formatted_string+'T00:00:00.000+0000')


def to_jira_formatted_date(datetime_object):
    return datetime_object.strftime("%Y-%m-%d")


def matches(str_a, str_b):
    return str_a is not None and str_b is not None and str_a.lower() == str_b.lower()


def transition_issue(key, transition_string, additional_fields, id_lookup_method=None, **kwargs):
    jira = get_jira()
    issue = jira.issue(key)
    issue_type_name = issue_mappings.Type(issue)
    project_key = issue.fields().project.key
    [transition] = [item['id'] for item in jira.transitions(issue) if matches(item['name'], transition_string)]
    fields = dict()
    if additional_fields:
        for key, value in list(additional_fields.items()):
            if key in ('issuelinks', ):
                fields[key] = value
            else:
                fields[get_custom_fields()[key]] = _compute_value(key, value, id_lookup_method)
    logger.debug("calling transition_issue(issue={issue!r}, transition={transition!r}, fields={fields!r})".format(issue=issue, transition=transition, fields=fields))
    jira.transition_issue(issue=issue.key, transition=transition, fields=fields, **kwargs)


def resolve_issue(key, resolution_string, fix_versions_strings):
    jira = get_jira()
    issue = jira.issue(key)
    [resolution] = [item.id for item in jira.resolutions() if matches(item.name, resolution_string)]
    project_versions = jira.project_versions(issue.fields().project)
    fix_versions = [dict(id=item.id) for item in project_versions if item.name in fix_versions_strings]
    fields = dict(resolution=dict(id=resolution), fixVersions=fix_versions)
    transition_issue(key, "Resolve Issue", dict(), **fields)


def start_progress(key):
    transition_issue(key, "Start Progress", dict())


def stop_progress(key):
    transition_issue(key, "Stop Progress", dict())


def reopen(key):
    transition_issue(key, "Reopen Issue", dict())


def iter_projects():
    for item in get_jira().projects():
      yield get_project(item.key)


@cached_function
def get_project(key):
    return get_jira().project(key.upper())


@cached_function
def get_version(key, name):
    [version] = [version for version in get_project(key).versions if version.name == name]
    return version


@cached_function
def get_next_release_name_for_issue(key):
    jira = get_jira()
    issue = jira.issue(key)
    project = issue.fields().project.key
    return get_next_release_name_in_project(project)


@cached_function
def get_next_release_name_in_project(key):
    project = get_project(key)
    next_releases = sorted([version for version in project.versions if not version.released],
                           key=lambda version: from_jira_formatted_date(getattr(version, "releaseDate", '2121-12-12')))
    if next_releases:
      return next_releases[0].name
    return ''


@cached_function
def _get_options(customfield_name):
    config = Configuration.from_file()
    customfield_id = get_custom_fields()[customfield_name]
    options = requests.get(get_jira_url(GET_URI.format(customfield_id=customfield_id)),
                           auth=get_auth(config.jira_fqdn),
                           headers=get_headers()).json()
    return options


def get_custom_field_values(customfield_name):
    options = _get_options(customfield_name)
    return [item['optionvalue'] for item in options]


def get_enabled_custom_field_values(customfield_name):
    options = _get_options(customfield_name)
    return [item['optionvalue'] for item in options if not item['disabled']]


def get_custom_field_value_id_from_createmeta(project_key, issue_type_name, key, value):
    result = get_jira().createmeta(issuetypeNames=[issue_type_name], projectKeys=[project_key], expand=['projects.issuetypes.fields'])
    values = result['projects'][0]['issuetypes'][0]['fields'][get_custom_fields()[key]]['allowedValues']
    [value_id] = [item['id'] for item in values if item['value'] == value]
    return value_id


def _compute_value(key, value, id_lookup_method):
    def _translate(value):
        if key in ('issuelinks', ):
          return value
        if 'select' in get_custom_fields_schema()[key]:
          return {'value': value}
        if 'radiobuttons' in get_custom_fields_schema()[key]:
          return {'id': id_lookup_method(key, value)}
        if 'multicheckboxes' in get_custom_fields_schema()[key]:
          return {'id': id_lookup_method(key, value)}
        if 'userpicker' in get_custom_fields_schema()[key]:
          return {'name': value}
        return value

    if isinstance(value, (list, tuple)):
      return [_translate(item) for item in value]
    result = _translate(value)
    return result if isinstance(result, dict) else result


def create_issue(project_key, issue_type_name, component_name, fix_version_name, details, assignee=None, parent=None, additional_fields=None, id_lookup_method=None):
    jira = get_jira()
    project = jira.project(project_key)
    [issue_type] = [issue_type for issue_type in project.issueTypes
                                    if matches(issue_type.name, issue_type_name)]
    components = [component for component in project.components
                                if matches(component.name, component_name)]
    versions = [version for version in project.versions
                            if matches(version.name, fix_version_name)]
    summary = details.split("\n", 1)[0]
    description = details.split("\n", 1)[1:]
    fields = dict(project=dict(id=str(project.id)),
                  issuetype=dict(id=str(issue_type.id)),
                  components=[dict(id=str(component.id)) for component in components],
                  fixVersions=[dict(id=str(version.id)) for version in versions],
                  summary=summary, description=description[0] if description else None)
    if not fields['description']:
      fields.pop('description')
    if assignee:
      fields['assignee'] = dict(name=assignee)
    if parent:
      fields['parent'] = dict(key=parent)
    if not versions:
        fields.pop('fixVersions')
    if not components:
        fields.pop('components')
    if additional_fields:
        for key, value in list(additional_fields.items()):
            _id_lookup_method = id_lookup_method or partial(get_custom_field_value_id_from_createmeta, project_key=project_key, issue_type_name=issue_type_name)
            fields[get_custom_fields()[key]] = _compute_value(key, value, _id_lookup_method)
    issue = jira.create_issue(fields=fields)
    return issue


def create_link(link_type_name, from_key, to_key):
    jira = get_jira()
    [link_type] = [link_type for link_type in jira.issue_link_types()
                                 if matches(link_type.name, link_type_name)]

    kwargs = dict(type=link_type.name, inwardIssue=from_key, outwardIssue=to_key)
    jira.create_issue_link(**kwargs)


def search_issues(query, maxResults=2000, expand=None):
    jira = get_jira()
    return jira.search_issues(query, maxResults=maxResults, expand=expand)


def comment_on_issue(key, message):
    get_jira().add_comment(issue=key, body=message)


@cached_function
def get_issue(key):
    return get_jira().issue(key.upper())


@cached_function
def get_query_by_filter(name):
    """:returns: the jql of the filter"""
    for _filter in get_jira().favourite_filters():
        if _filter.name == name:
            return _filter.jql
    raise JIRAError(404, "no such filter")


issue_mappings = Munch(Rank=lambda issue: int(issue.fields().customfield_10700),
                       Type=lambda issue: issue.fields().issuetype.name,
                       Key=lambda issue: issue.key,
                       Summary=lambda issue: issue.fields().summary,
                       Description=lambda issue: issue.fields().description,
                       Priority=lambda issue: issue.fields().priority.name,
                       Project=lambda issue: issue.fields().project.name,
                       Status=lambda issue: issue.fields().status.name,
                       Resolution=lambda issue: (issue.fields().resolution or Munch(name="Unresolved")).name,
                       Created=lambda issue: from_jira_formatted_datetime(issue.fields().created),
                       Updated=lambda issue: from_jira_formatted_datetime(issue.fields().updated),
                       Assignee=lambda issue: issue.fields().assignee.displayName,
                       Reporter=lambda issue: issue.fields().reporter.displayName,
                       Labels=lambda issue: issue.fields().labels,
                       Comments=lambda issue: issue.fields().comment.comments,
                       AffectsVersions=lambda issue: [item.name for item in getattr(issue.fields(), 'versions', list())],
                       FixVersions=lambda issue: [item.name for item in getattr(issue.fields(), 'fixVersions', list())],
                       Components=lambda issue: [item.name for item in issue.fields().components],
                       IssueLinks=lambda issue: issue.fields().issuelinks,
                       SubTasks=lambda issue: issue.fields().subtasks,
                       Attachments=lambda issue: issue.fields().attachment,
                       )


@cached_function
def is_user_exists(username):
    return any(user.key == username for user in get_jira().search_users(username))


@cached_function
def get_user_by_name(name):
     users = get_jira().search_users(name)
     return users[0].key if len(users) == 1 else None


from .custom_field_editor import get_options_for_custom_field, get_custom_field_id_by_name
