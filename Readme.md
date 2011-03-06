ct - Company Time
=================

`ct` is a git-based time tracking tool requiring Python 2.7 and `python-dateutil`.

Workflow
--------

To start tracking time, make a git repository and type `ct init` at the repository root.

When you begin working, type `ct clockin [project_name]`. When you are done, type `ct clockout`. To change projects, type `ct clockin [new_project]`.

To allow others to track time on the same projects, push the git repository to some central storage location like Github.

To join an existing project, clone the project's `ct` repository. You will have to answer a prompt the first time you `clockin`.

Commands
--------

Usage: `ct [command]`

    init: Create or replace the config file in the current directory
    clockin [project_name]: Begin tracking hours on a project
    clockout: Stop tracking hours
    tally [project_name]: Count all hours spent working on a project

Optional Arguments
------------------

You can provide a `-t [time string]` argument to `clockin` and `clockout` to use that time instead of the current time. Add `--help` to any command to get the full usage of that command.

To Do
-----

* Allow tally of all projects and display summary
* Show hours per person when showing hours for a project
