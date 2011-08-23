from contextlib import contextmanager
import datetime
import json
import logging
import os
import re
import sys

from dateutil.parser import parse as parse_date

log = logging.getLogger('companytime.commands')

now = datetime.datetime.now()

file_date_format = '%m-%d-%Y %H:%M:%S'

year_re = re.compile('%d%d%d%d')

### Manipulating the config file ###

def working_directory():
    return os.environ['CT_HOME']

def config_file_path():
    return os.path.join(working_directory(), 'config')

@contextmanager
def config(mode='r'):
    """Convenient way to read the config file"""
    with open(config_file_path(), mode) as f:
        yield f

def init():

    def sanitize(name):
        name.replace('/', '_')
        name.replace('\\', '_')
        name.replace(':', '_')
        name.replace('\n', '_')
        return name

    name = ''
    while not name:
        name = sanitize(raw_input('Your name in filesystem-legal characters:\n'))

    with config('w') as conf:
        json.dump({'name': name}, conf)

    log.info('Created config file')

def load_config():
    """Load or create the config file"""
    if not os.path.exists(config_file_path()):
        init()
    with config() as conf:
        return json.load(conf)

### Parsing ###

def parse_date_from_file(date_string):
    return datetime.datetime.strptime(date_string.strip(), file_date_format)

def parse_date_range_args(tfrom, tto):
    from_time = parse_date(tfrom) if tfrom else None
    to_time = parse_date(tto) if tto else None
    return from_time, to_time

def parse_clockin(line):
    project, date_string = line.split(' clockin ', 1)
    return project, parse_date_from_file(date_string)

def parse_clockout(line):
    return parse_date_from_file(line.split('clockout ', 1)[1].strip())

def write_clockin(project, time):
    writeln('%s clockin %s\n' % (project, time.strftime(file_date_format)))

def write_clockout(time):
    writeln('clockout %s\n' % (time.strftime(file_date_format)))

def hours_and_minutes_from_seconds(s):
    hours = s // 3600
    s -= hours * 3600
    minutes = s // 60
    return hours, minutes

### Files ###

def file_for_current_user(mode='r'):
    """Return the file corresponding to the current user"""
    config = load_config()
    path = os.path.join(working_directory(), '%s.txt' % config['name'])
    if mode == 'r' and not os.path.exists(path):
        return None
    else:
        return open(path, mode)

def all_files(mode='r'):
    wd = working_directory()
    paths = (path for path in os.listdir(wd) if path.endswith('.txt'))
    return [open(os.path.join(wd, path), mode) for path in paths]

def writeln(line):
    """Write a line to the current user's file"""
    with file_for_current_user('a') as f:
        f.write(line)
