from infi.pyutils.lazy import cached_function
from bunch import Bunch


ASSIGNED_TO_ME = "assignee = currentUser() AND resolution = unresolved ORDER BY priority DESC, created ASC"


@cached_function
def get_jira():
    from .config import Configuration
    from jira.client import JIRA
    config = Configuration.from_file()
    options = dict(server="http://{0}".format(config.fqdn))
    basic_auth = (config.username, config.password)
    return JIRA(options, basic_auth)


def get_issues__assigned_to_me():
    return get_jira().search_issues(ASSIGNED_TO_ME)


def add_labels_to_issue(key, labels):
    issue = get_issue(key)
    labels = set.union(set([unicode(label) for label in labels]), set(issue.fields().labels))
    issue.update(labels=list(labels))


def assign_issue(key, assignee):
    get_jira().assign_issue(key, assignee)


def from_jira_formatted_datetime(formatted_string):
    # http://stackoverflow.com/questions/127803/how-to-parse-iso-formatted-date-in-python
    import re
    import datetime
    return datetime.datetime(*map(int, re.split('[^\d]', formatted_string)[:-1]))


def from_jira_formatted_date(formatted_string):
    return from_jira_formatted_datetime(formatted_string+'T00:00:00.000+0000')

def matches(str_a, str_b):
    return str_a is not None and str_b is not None and str_a.lower() == str_b.lower()

def transition_issue(key, transition_string, fields):
    jira = get_jira()
    issue = jira.issue(key)
    [transition] = [item['id'] for item in jira.transitions(issue) if matches(item['name'], transition_string)]
    jira.transition_issue(issue=issue.key, transitionId=transition, fields=fields)


def resolve_issue(key, resolution_string, fix_versions_strings):
    jira = get_jira()
    issue = jira.issue(key)
    [resolution] = [item.id for item in jira.resolutions() if matches(item.name, resolution_string)]
    project_versions = jira.project_versions(issue.fields().project)
    fix_versions = [dict(id=item.id) for item in project_versions if item.name in fix_versions_strings]
    fields = dict(resolution=dict(id=resolution), fixVersions=fix_versions)
    transition_issue(key, "Resolve Issue", fields)


def start_progress(key):
    transition_issue(key, "Start Progress", dict())


def stop_progress(key):
    transition_issue(key, "Stop Progress", dict())


def get_next_release_name(key):
    jira = get_jira()
    issue = jira.issue(key)
    project = issue.fields().project
    versions = jira.project_versions(project)
    return sorted([version for version in versions if not version.released],
                  key=lambda version: from_jira_formatted_date(getattr(version, "releaseDate", '2121-12-12')))[0].name


def create_issue(project_key, summary, component_name, issue_type_name):
    jira = get_jira()
    project = jira.project(project_key)
    [issue_type] = [issue_type for issue_type in project.issueTypes
                    if matches(issue_type.name, issue_type_name)]
    components = [component for component in project.components
                    if matches(component.name, component_name)]
    fields = dict(project=dict(id=str(project.id)), summary=summary,
                  components=[dict(id=str(component.id)) for component in components],
                  issuetype=dict(id=str(issue_type.id)))
    issue = jira.create_issue(fields=fields)
    return issue


def create_link(link_type_name, from_key, to_key, comment):
    jira = get_jira()
    [link_type] = [link_type for link_type in jira.issue_link_types()
                   if matches(link_type.name, link_type_name)]

    kwargs = dict(type=link_type.name, inwardIssue=from_key, outwardIssue=to_key)
    if comment:
        kwargs.update(**dict(comment=dict(body=comment)))
    jira.create_issue_link(**kwargs)


def search_issues(query):
    jira = get_jira()
    return jira.search_issues(query, maxResults=100)


@cached_function
def get_issue(key):
    return get_jira().issue(key.upper())


issue_mappings = Bunch(Rank=lambda issue: int(issue.fields().customfield_10700),
                    Type=lambda issue: issue.fields().issuetype.name,
                    Key=lambda issue: issue.key,
                    Summary=lambda issue: issue.fields().summary,
                    Description=lambda issue: issue.fields().description,
                    Priority=lambda issue: issue.fields().priority.name,
                    Project=lambda issue: issue.fields().project.name,
                    Status=lambda issue: issue.fields().status.name,
                    Resolution=lambda issue: (issue.fields().resolution or Bunch(name="Unresolved")).name,
                    Created=lambda issue: from_jira_formatted_datetime(issue.fields().created),
                    Updated=lambda issue: from_jira_formatted_datetime(issue.fields().updated),
                    Assignee=lambda issue: issue.fields().assignee.displayName,
                    Reporter=lambda issue: issue.fields().reporter.displayName,
                    Labels=lambda issue: issue.fields().labels,
                    Comments=lambda issue: issue.fields().comment.comments,
                    AffectsVersions=lambda issue: [item.name for item in issue.fields().versions],
                    FixVersions=lambda issue: [item.name for item in issue.fields().fixVersions],
                    Components=lambda issue: [item.name for item in issue.fields().components],
                    IssueLinks=lambda issue: issue.fields().issuelinks,
                    SubTasks=lambda issue: issue.fields().subtasks,
                    )
