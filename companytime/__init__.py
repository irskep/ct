#!/usr/bin/python

import argparse
import datetime
import os
import sys

from dateutil.parser import parse as parse_date

config_file_name = '.ctconfig'
file_date_format = '%m-%d-%Y %H:%M:%S'
user_date_format = '%I:%M %p on %b %d, %Y'
now = datetime.datetime.now()

# =====================
# = Utility functions =
# =====================

def sanitize(name):
    name.replace('/', '_')
    name.replace('\\', '_')
    name.replace(':', '_')
    name.replace('\n', '_')
    return name

def parse_date_from_file(date_string):
    return datetime.datetime.strptime(date_string.strip(), file_date_format)

def parse_date_range_args(tfrom, tto):
    from_time = parse_date(tfrom) if tfrom else None
    to_time = parse_date(tto) if tto else now
    
    while now < to_time:
        to_time = to_time.replace(year=to_time.year-1)
    while (from_time is not None and to_time < from_time):
        from_time = from_time.replace(year=from_time.year-1)
    return from_time, to_time

def parse_clockin(line):
    project, date_string = line.split(' clockin ')
    return project, parse_date_from_file(date_string)

def parse_clockout(line):
    return parse_date_from_file(line.split('clockout ')[1].strip())

def hours_and_minutes_from_seconds(s):
    hours = s // 3600
    s -= hours * 3600
    minutes = s // 60
    return hours, minutes

def load_config():
    """Load or create the config file"""
    if not os.path.exists(config_file_name):
        init()
    config = {}
    with open(config_file_name) as f:
        for line in f:
            k, v = line.split(':')
            config[k] = v.strip()
    return config

def file_for_current_user(mode='r'):
    """Return the file corresponding to the current user"""
    config = load_config()
    path = '%s.txt' % config['name']
    if mode == 'r' and not os.path.exists(path):
        return None
    else:
        return open(path, mode)

def all_files(mode='r'):
    paths = (path for path in os.listdir('.') if path.endswith('.txt'))
    return [open(path, mode) for path in paths]

def log(line):
    """Write a line to the current user's file"""
    with file_for_current_user('a') as f:
        f.write(line)

def clocked_in_info():
    """Return True if a user is configured and the last action was a clockin"""
    f = file_for_current_user()
    if f:
        last_line = f.readlines()[-1]
        if 'clockin' in last_line:
            return parse_clockin(last_line)
        else:
            return None, None
    else:
        return None, None


# ============
# = Commands =
# ============

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
            sys.exit[0]
    
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

@command('tally')
def tally(args):
    parser = argparse.ArgumentParser(prog='ct tally',
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
    
    if from_time or to_time != now:
        print "Periods are only counted if their start and end times are within \n    the given range."

def main():
    parser = argparse.ArgumentParser(prog='ct',
                                     description='Time tracking tool')
    parser.add_argument('command', type=str, action='store',
                        choices=commands.keys(),
                        help='init, clockin, or clockout')
    args = parser.parse_args(sys.argv[1:2])
    commands[args.command](sys.argv[2:])

if __name__ == '__main__':
    main()
