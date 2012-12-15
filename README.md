Overview
========
A small command-line tool for those things in JIRA that we do several times a day.


Installation Instructions
=========================

1. Install the package

    easy_install -U infi.jira_cli

2. Install the shell completion helper

    easy_install -U infi.docopt_completion
    docopt-completion jissue

3. Set-up your JIRA information

    jissue config set jira.your.domain your-username your-password


Usage
=========================

    jissue
    infinidat jira issue command-line tool

    Usage:
        jissue list [--sort-by=<column-name>]
        jissue start <issue>
        jissue stop <issue>
        jissue resolve <issue> <message> [--fix-version=<version>]
        jissue duplicate <issue> <duplicate-ticket> <message>
        jissue reject <issue> <reason> <message>
        jissue config show
        jissue config set <fqdn> <username> <password>

    Options:
        --sort-by=<column-name>     column to sort by [default: Rank]
        --help                      show this screen
        <reason>                    resolution type, e.g. "won't fix"

    More Information:
        jissue list                 lists open issues
        jissue start                start progress
        jissue stop                 stop progress
        jissue resolve              resolve an open issue as fixed
        jissue duplicate            resolve an issue as a duplicate, with link to the duplicated issue
        jissue reject               resolved an open issue not as fixed

 
Checking out the code
=====================

You must install the dependencies first:

    easy_install -U infi.projector

and then, run:

    projector devenv build

