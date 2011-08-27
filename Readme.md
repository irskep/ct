ct - Cut Time
=================

`ct` is a time tracking tool requiring Python 2.7 and `python-dateutil`. If you
are on a Mac, it can update your Adium status with what you are working on.

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

The `clockin` and `clockout` commands both take a `--time` argument to specify
a time other than now. If you have Adium, you can also specify `--away` to have
your status set to Away instead of Available in addition to having your status
message updated.
