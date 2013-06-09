Overview
========
A small set of command-line tools for those things in JIRA that we do several times a day.


Example
-------
With jissue, you can do the following:

    jissue create MYPROJECT "THIS IS A TICKET"

This prints out the ticket information, and with that you can do:

    jissue comment <TICKET> "this is my comment"


Virtualenv-style
----------------
If you work with JIRA alot, its annoying to type in the project/issue key all the sime
Starting from version 0.1, jissue ships with `jish`, which is a shell wrapper, similar to `virtualenv`.
`jish` sets up the following environment variables: `JISSUE_PROJECT`, `JISSUE_VERSION`, `JISSUE_COMPONENT`, `JISSUE_ISSUE`, which `jissue` treats as defaults. You can use this variables to set up your zsh prompt.
Here's a simple demonstration to show when this is useful:

    jish project MYPROJECT # by default, it uses the upcoming unreleased version, and 'unknown component'
    jish create "this is a test" "this is an optional description"
    jissue commit file-a file-b --mesage="this message will be appended to the ticket numeber"
    jissue comment "you can also just comment on the ticket without mentioning it explicitly"
    jihs resolve  # this will deactivate


Installation Instructions
=========================

Install the package

    easy_install -U infi.jira_cli


Install the shell wrapper and completion

    setup-jish unattended


Set-up your JIRA information

    jissue config set jira.your.domain your-username your-password


Checking out the code
=====================

You must install the dependencies first:

    easy_install -U infi.projector

and then, run:

    projector devenv build


Running tests
=============

Before running the tests, you'll need set the jira configuration and pass some environment variables to nose:

    TEST_PROJECT= bin/nosetests
