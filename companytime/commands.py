#!/usr/bin/python

import argparse
import datetime
import os
import sys

from dateutil.parser import parse as parse_date

from companytime.util import all_files, clocked_in_info, hours_and_minutes_from_seconds, now, parse_clockin, parse_clockout, parse_date_range_args, sanitize

config_file_name = '.ctconfig'
file_date_format = '%m-%d-%Y %H:%M:%S'
user_date_format = '%I:%M %p on %b %d, %Y'

commands = {}

def command(name):
    """Declare a command"""
    def dec(func):
        commands[name] = func
        return func
    return dec

@command('init')
def init(args=None):
    args = args or []
    parser = argparse.ArgumentParser(prog='ct init',
                                     description='Start tracking time in an empty repository')
    args = parser.parse_args(args)

    try:
        name = sanitize(raw_input('Your name in filesystem-legal characters:\n'))
    except EOFError:
        if os.path.exists(config_file_name):
            print 'Keeping old config'
            return
        else:
            print 'Exiting'
            sys.exit(0)

    try:
        os.remove(config_file_name)
    except OSError:
        pass    # Doesn't matter

    with open(config_file_name, 'w') as f:
        f.write('name: %s\n' % name)

    print 'Created config file'

@command ('clockin')
def clockin(args):
    parser = argparse.ArgumentParser(prog='ct clockin',
                                     description='Start logging hours to a project')
    parser.add_argument('project', type=str, action='store',  nargs='+')
    parser.add_argument('-t', '--time', type=str, action='store', default=None,
                        help='Time to log for checkin')

    args = parser.parse_args(args)
    proj = ' '.join(args.project)

    project, clockin_time = clocked_in_info()
    if project:
        clockout()

    clockin_time = parse_date(args.time) if args.time else now

    log('%s clockin %s\n' % (proj, clockin_time.strftime(file_date_format)))

    print 'Clocked into %s at %s' % (proj,
                                     clockin_time.strftime(user_date_format))

@command ('clockout')
def clockout(args=None):
    args = args or []
    parser = argparse.ArgumentParser(prog='ct clockout',
                                     description='Stop logging hours to a project')
    parser.add_argument('-t', '--time', type=str, action='store', default=None,
                        help='Time to log for checkin')

    args = parser.parse_args(args)

    clockout_time = parse_date(args.time) if args.time else now

    project, clockin_time = clocked_in_info()

    if project:
        if clockout_time >= clockin_time:
            log('clockout %s\n' % (clockout_time.strftime(file_date_format)))

            print 'Clocked out of %s at %s' % (project, 
                                               clockout_time.strftime(user_date_format))
        else:
            print 'Clockout time is before last clockin time. Clockout failed.'
    else:
        print 'Not clocked into anything. Clockout failed.'

@command('summary')
def summary(args):
    parser = argparse.ArgumentParser(prog='ct summary',
                                     description='Count hours spent on a project')
    parser.add_argument('project', type=str, action='store',  nargs='*')
    parser.add_argument('-m', '--more_projects', type=str, action='store', nargs='+',
                        default=[])
    parser.add_argument('-f', dest='tfrom', type=str, action='store', default=None,
                        help='When to start counting')
    parser.add_argument('-t', dest='tto', type=str, action='store', default=None,
                        help='When to stop counting')
    parser.add_argument('-v', '--verbose', action='store_const', const=True, default=False)

    args = parser.parse_args(args)
    proj = ' '.join(args.project)
    if proj:
        projects = [proj] + args.more_projects
    else:
        projects = args.more_projects
    if not projects:
        projects = None

    from_time, to_time = parse_date_range_args(args.tfrom, args.tto)

    total_time = datetime.timedelta()

    for file in all_files('r'):
        with file as f:
            lines = f.readlines()
        i = 0
        while i < len(lines)-1: # Don't count non-clocked-out sessions
            line = lines[i].strip()
            this_proj, clockin_time = parse_clockin(line)
            clockout_time = parse_clockout(lines[i+1])
            if this_proj in projects or projects is None:
                if from_time is None or clockin_time >= from_time:
                    if clockout_time < to_time:
                        total_time += clockout_time - clockin_time
                        if args.verbose:
                            print "%s - %s" % (clockin_string, clockout_string)
            i += 2

    print '%d hours, %d minutes' % hours_and_minutes_from_seconds(total_time.seconds)

    if from_time or to_time != now: print "Periods are only counted if their start and end times are within \n    the given range."
