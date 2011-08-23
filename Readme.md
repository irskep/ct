ct - Company Time
=================

`ct` is a time tracking tool requiring Python 2.7 and `python-dateutil`.

Workflow
--------

To start tracking time, create a working directory for `ct` (e.g. `~/.ct`) and set the `$CT_HOME` environment variable. This directory can be used as a Git repository.

When you begin working, type `ct clockin [project_name]`. When you are done, type `ct clockout`. To change projects, type `ct clockin [new_project]`.

Commands
--------

Usage: `ct [command]`

    init: Create or replace the config file in the current directory
    clockin [project_name]: Begin tracking hours on a project
    clockout: Stop tracking hours
    summary [project_name]: Count and display hours spent on one or all projects

Optional Arguments
------------------

You can provide a `-t [time string]` argument to `clockin` and `clockout` to use that time instead of the current time. Add `--help` to any command to get the full usage of that command.
