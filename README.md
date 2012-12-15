Overview
========
A small command-line tool for those things in JIRA that we do several times a day.


Installation Instructions
=========================

Install the package

    easy_install -U infi.jira_cli

Install the shell completion helper

    easy_install -U infi.docopt_completion
    docopt-completion jissue

Set-up your JIRA information

    jissue config set jira.your.domain your-username your-password


Usage
=========================

    jissue
    infinidat jira issue command-line tool

    Usage:
        jissue list [--sort-by=<column-name>] [--reverse]
        jissue start <issue>
        jissue stop <issue>
        jissue show <issue>
        jissue create <project> <summary> [--issue-type=<issue-type>] [--component=<component>]
        jissue comment <issue> <message>
        jissue resolve <issue> <message> [--resolve-as=<resolution>] [--fix-version=<version>]
        jissue link <issue> <target-issue> <message>
        jissue config show
        jissue config set <fqdn> <username> <password>

    Options:
        --sort-by=<column-name>      column to sort by [default: Rank]
        --resolve-as=<resolution>    resolution string [default: Fixed]
        --issue-type=<issue-type>    issue type string [default: Bug]
        --help                       show this screen

    More Information:
        jissue list                 lists open issues assigned to selffg
        jissue start                start progress
        jissue stop                 stop progress
        jissue create               create a new issue
        jissue comment              add a comment to an existing issue
        jissue resolve              resolve an open issue as fixed
        jissue link                 link between two issues
     

Checking out the code
=====================

You must install the dependencies first:

    easy_install -U infi.projector

and then, run:

    projector devenv build

