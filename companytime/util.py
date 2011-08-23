import datetime
import os

now = datetime.datetime.now()

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
