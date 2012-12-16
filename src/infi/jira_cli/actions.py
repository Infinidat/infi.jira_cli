from __future__ import print_function


def format(value, slice=None):
    from datetime import datetime
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, (list, tuple)):
        return ', '.join(value)
    return str(value)[:slice]


def list_issues(arguments):
    from .jira_adapter import get_issues__assigned_to_me, from_jira_formatted_datetime, issue_mappings
    columns = ["Rank", "Type", "Key", "Summary", "Status", "Created", "Updated"]
    FORMAT = "{:<8}{:<15}{:<20}{:<50}{:<15}{:<20}{:<20}"
    sortby_column = arguments.get("--sort-by").capitalize()
    reverse = arguments.get("--reverse")
    data = [{column: issue_mappings[column](issue) for column in columns}
            for issue in get_issues__assigned_to_me()]
    sorted_data = sorted(data, key=lambda item: item[sortby_column], reverse=reverse)

    print(FORMAT.format(*columns))
    for item in sorted_data:
        print(FORMAT.format(*[format(item[column], 47) for column in columns]))


def start(arguments):
    raise NotImplementedError()


def stop(arguments):
    raise NotImplementedError()


def show(arguments):
    from textwrap import dedent
    template = """
    {Project} / {Key}
    {Summary}

    Type:              {Type:<11}                       Status:        {Status:<15}            Assignee: {Assignee:<15}
    Priority:          {Priority:<15}                   Resolution:    {Resolution:<19}        Reporter: {Reporter}
    Affects Version/s: {Affects Version/s:<24}          Fix Version/s: {Fix Version/s:<26}
    Components: {Component/s:<60}                       Created: {Created}
    Labels: {Labels:<55}                                Updated: {Updated}

    Description:
    {Description}

    Comments:
    {Comments}
    """
    keywords = ["Project", "Key", "Summary", "Type", "Status",
                "Priority", "Resolution", "Assignee", "Reporter",
                "Affects Version/s", "Fix Version/s", "Component/s",
                "Created", "Updated", "Labels",
                "Description", "Comments"]
    from .jira_adapter import get_issue, issue_mappings
    issue = get_issue(arguments.get("<issue>"))
    kwargs = {item: format(issue_mappings[item](issue)) for item in keywords}
    print(dedent(template.format(**kwargs)))


def comment(arguments):
    from .jira_adapter import comment_on_issue
    comment_on_issue(arguments.get("<issue>"), arguments.get("<message>"))


def resolve(arguments):
    from .jira_adapter import resolve_issue, get_next_release_name
    key = arguments.get("<issue>")
    message = arguments.get("<message>")
    fix_version = arguments.get("--fix-version") or get_next_release_name(key)
    resolution = arguments.get("--resolve-as")
    resolve_issue(key, resolution, [fix_version])
    comment(arguments)


def link(arguments):
    raise NotImplementedError()


def create(arguments):
    from .jira_adapter import create_issue
    project_key = arguments.get("<project>").upper()
    summary = arguments.get("<summary>")
    component_name = arguments.get("--component")
    issue_type_name = arguments.get("--issue-type")
    issue = create_issue(project_key, summary, component_name, issue_type_name)
    show({"<issue>": issue.key})


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
        config=dict(show=config_show, set=config_set)
    )


def choose_action(argv):
    argv = argv[::-1]
    mappings = get_mappings()
    while True:
        keyword = argv.pop()
        mappings = mappings[keyword]
        if hasattr(mappings, "__call__"):
            return mappings
