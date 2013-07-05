from __future__ import print_function


def format(value, slice=None):
    from datetime import datetime
    from jira.resources import Comment, Issue, IssueLink
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, (list, tuple)):
        if len(value) and isinstance(value[0], (Comment, )):
            from .jira_adapter import from_jira_formatted_datetime
            return "\n\n".join([u"{0} added a comment - {1}\n{2}".format(item.author.displayName,
                                                                         format(from_jira_formatted_datetime(item.created)),
                                                                         item.body)
                                for item in value])
        if len(value) and isinstance(value[0], (IssueLink, )):
            from .jira_adapter import issue_mappings
            get_linked_issue = lambda item: getattr(item, "inwardIssue", getattr(item, "outwardIssue", None))
            get_link_text = lambda item: item.type.inward if hasattr(item, "inwardIssue") else item.type.outward
            return "\n\n".join(["u{0:<20} {1:<15} {2:<15} {3}".format(get_link_text(item),
                                                                      issue_mappings['Key'](get_linked_issue(item)),
                                                                      issue_mappings['Status'](get_linked_issue(item)),
                                                                      issue_mappings['Summary'](get_linked_issue(item)))
                                for item in value])
        if len(value) and isinstance(value[0], (Issue, )):
            from .jira_adapter import issue_mappings
            return "\n".join(["u{0:<20} {1:<15} {2:<15} {3}".format('',
                                                                    issue_mappings['Key'](item),
                                                                    issue_mappings['Status'](item),
                                                                    issue_mappings['Summary'](item))
                              for item in value])
        return ', '.join(value)
    return unicode(value)[:slice]


def _list_issues(arguments, issues):
    from .jira_adapter import from_jira_formatted_datetime, issue_mappings
    columns = ["Rank", "Type", "Key", "Summary", "Status", "Created", "Updated"]
    FORMAT = "{:<8}{:<15}{:<20}{:<50}{:<15}{:<20}{:<20}"
    sortby_column = arguments.get("--sort-by").capitalize()
    reverse = arguments.get("--reverse")
    data = [{column: issue_mappings[column](issue) for column in columns}
            for issue in issues]
    sorted_data = sorted(data, key=lambda item: item[sortby_column], reverse=reverse)

    print(FORMAT.format(*columns))
    for item in sorted_data:
        try:
            print(FORMAT.format(*[format(item[column], 47) for column in columns]))
        except UnicodeEncodeError:
            pass


def list_issues(arguments):
    from .jira_adapter import get_issues__assigned_to_me, get_issues__assigned_to_user
    user = arguments.get("--assignee")
    project = arguments.get("<project>")
    issues = get_issues__assigned_to_user(user, project) if user else get_issues__assigned_to_me(project)
    _list_issues(arguments, issues)


def search(arguments):
    from .jira_adapter import search_issues
    return _list_issues(arguments, search_issues(arguments.get("<query>")))


def start(arguments):
    from .jira_adapter import start_progress
    start_progress(arguments.get("<issue>"))


def stop(arguments):
    from .jira_adapter import stop_progress
    stop_progress(arguments.get("<issue>"))


def show(arguments):
    from textwrap import dedent
    from string import printable
    template = u"""
    {Project} / {Key}
    {Summary}

    Type:              {Type:<11}                       Status:        {Status:<15}            Assignee: {Assignee:<15}
    Priority:          {Priority:<15}                   Resolution:    {Resolution:<19}        Reporter: {Reporter}
    Affects Version/s: {AffectsVersions:<22}            Fix Version/s: {FixVersions:<26}
    Components: {Components:<59}                        Created: {Created}
    Labels: {Labels:<55}                                Updated: {Updated}

    Issue Links:
    {IssueLinks}

    Sub-Tasks:
    {SubTasks}

    Description:
    {Description}

    Comments:
    {Comments}
    """
    keywords = ["Project", "Key", "Summary", "Type", "Status",
                "Priority", "Resolution", "Assignee", "Reporter",
                "AffectsVersions", "FixVersions", "Components",
                "Created", "Updated", "Labels",
                "Description", "Comments", "IssueLinks", "SubTasks"]
    from .jira_adapter import get_issue, issue_mappings
    issue = get_issue(arguments.get("<issue>"))
    kwargs = {item: format(issue_mappings[item](issue)) for item in keywords}
    data = dedent(template).format(**kwargs)
    data = ''.join([item for item in data if item in printable])
    print(data)


def comment(arguments):
    from .jira_adapter import comment_on_issue
    comment_on_issue(arguments.get("<issue>"), arguments.get("<message>"))


def resolve(arguments):
    from .jira_adapter import resolve_issue, get_next_release_name_for_issue
    from string import capwords
    key = arguments.get("<issue>")
    fix_version = arguments.get("--fix-version") or get_next_release_name_for_issue(key)
    resolution = capwords(arguments.get("--resolve-as"))
    resolve_issue(key, resolution, [fix_version])
    print("{0} resolved in version {1}".format(key, fix_version))


def link(arguments):
    from .jira_adapter import create_link
    from string import capwords
    create_link(capwords(arguments.get("<link-type>")), arguments.get("<issue>"), arguments.get("<target-issue>"))


def create(arguments):
    from .jira_adapter import create_issue, get_next_release_name_in_project
    from string import capwords
    project_key = arguments.get("<project>").upper()
    details = arguments.get("<details>")
    description = arguments.get("<description>")
    component_name = arguments.get("--component") or None
    issue_type_name = capwords(arguments.get("<issue-type>"))
    fix_version_name = arguments.get("--fix-version") or get_next_release_name_in_project(project_key)
    component_name = arguments.get("--component")
    issue = create_issue(project_key, issue_type_name, component_name, fix_version_name, details)
    print(issue.key) if arguments.get("--short") else show({"<issue>": issue.key})
    return issue.key


def assign(arguments):
    from .jira_adapter import assign_issue
    from .config import Configuration
    key = arguments.get("<issue>")
    assignee = arguments.get("--assignee") if arguments.get("--assignee") else \
        "-1" if arguments.get("--automatic") else \
        Configuration.from_file().username if arguments.get("--to-me") else None  # --to-no-one
    assign_issue(key, assignee)


def config_show(arguments):
    from .config import Configuration
    try:
        print(Configuration.from_file().to_json(indent=True))
    except IOError:
        print("Configuration file does not exist")


def config_set(arguments):
    from .config import Configuration

    values = {item: getattr(arguments, "<{0}>".format(item))
              for item in ['fqdn', 'username', 'password']}
    config = Configuration(**values)
    config.save()


def inventory(arguments):
    from .jira_adapter import get_jira
    from string import capwords
    from pprint import pprint
    project_key = arguments.get("<project>")
    jira = get_jira()
    component_names = [item.name for item in jira.project_components(project_key)]
    unreleased_versions = [item.name for item in jira.project_versions(project_key) if not item.released]
    resolution_names = [item.name for item in jira.resolutions()]
    pprint({"Components": component_names, "Versions (unreleased)": unreleased_versions,
            "Resolve types": resolution_names})


def label(arguments):
    from .jira_adapter import add_labels_to_issue
    add_labels_to_issue(arguments.get("<issue>"), arguments.get("--label"))


def reopen(arguments):
    from .jira_adapter import reopen
    reopen(arguments.get("<issue>"))


def commit(arguments):
    from .jira_adapter import get_issue
    from .config import Configuration
    from infi.execute import execute_assert_success
    from sys import stdin, stdout, stderr
    from subprocess import Popen

    args = ["git", "commit"] + arguments.get("--file")
    message = arguments.get("<message>") or ''
    key = arguments.get("<issue>")
    issue = get_issue(key)
    summary = issue.fields().summary
    description = issue.fields().description
    username = Configuration.from_file().username
    args += ["--message", "{} @{} why do not put commit message".format(key, username),
             "--message", "Summary:\n{}".format(summary),
             "--message", "Description:\n{}".format(description)]
    if message:
        execute_assert_success(args)
    else:
        args += ["--edit"]
        Popen(args, stdout=stdout, stderr=stderr, stdin=stdin).wait()


def get_mappings():
    return dict(
        list=list_issues,
        start=start,
        stop=stop,
        show=show,
        create=create,
        comment=comment,
        resolve=resolve,
        link=link,
        inventory=inventory,
        assign=assign,
        search=search,
        label=label,
        commit=commit,
        reopen=reopen,
        config=dict(show=config_show, set=config_set),
    )


def choose_action(argv):
    argv = argv[::-1]
    mappings = get_mappings()
    while True:
        keyword = argv.pop()
        mappings = mappings[keyword]
        if hasattr(mappings, "__call__"):
            return mappings
