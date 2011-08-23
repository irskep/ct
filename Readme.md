ct - Company Time
=================

`ct` is a time tracking tool requiring Python 2.7 and `python-dateutil`.

Workflow
--------

Install with `python setup.py install`.

When you begin working, type `ct clockin [project_name]`. When you are done,
type `ct clockout`. To change projects, type `ct clockin [new_project]`. To
sum up all the hours spent on your projects, type `ct summary`.

You can instruct `ct` to use a working directory other than `~/.ct` by setting
`$CT_HOME`.

Commands
--------

Usage: `ct [command]`

    clockin [project_name]: Begin tracking hours on a project
    clockout: Stop tracking hours
    summary [project_name]: Count and display hours spent on one or all projects

Optional Arguments
------------------

You can provide a `-t [time string]` argument to `clockin` and `clockout` to
use that time instead of the current time. Add `--help` to any command to get
the full usage of that command.
