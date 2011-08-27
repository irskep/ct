#!/usr/bin/python

from argparse import ArgumentParser
from collections import defaultdict
import datetime
import logging
import os

from dateutil.parser import parse as parse_date

from cuttime import util
from cuttime.util import file_for_current_user, hours_and_minutes_from_seconds, last_project, load_config, now, parse_clockin, parse_clockout, parse_date_range_args, set_adium_status, writeln, write_clockin, write_clockout

user_date_format = '%I:%M %p on %b %d, %Y'

log = logging.getLogger('cuttime.commands')

adium_clockin_fmt = 'At %(location)s working on %(project)s. (updated %(time)s)'
adium_clockout_fmt = 'Not currently tracking time. Last seen at %(location)s working on %(project)s. (updated %(time)s)'
blurb = '\n\nThis message brought to you by ct (github.com/irskep/ct)'


commands = {}

def command(name):
    """Declare a command"""
    def dec(cls):
        commands[name] = cls()
        return cls
    return dec


class Command(object):

    description = '???'

    def clocked_in_info(self):
        """Return (project, date) if a user is configured and the last action was a
        clockin, otherwise (None, None)
        """
        with file_for_current_user() as f:
            if f:
                last_line = f.readlines()[-1]
                if 'clockin' in last_line:
                    return parse_clockin(last_line)
                else:
                    return None, None
            else:
                return None, None


class ActionCommand(Command):

    def add_arguments(self, parser):
        parser.add_argument('--away', default=False,
                            action='store_true', dest='away',
                            help='set Adium status to Away in addition to changing the message')

        parser.add_argument('-t', '--time', type=unicode, dest='time',
                            action='store', default=None,
                            help='time to log for checkin')

    def update_adium(self, format_str, project, time, away):
        conf = load_config()
        if conf['adium']:
            time_str = time.strftime(user_date_format)
            adium_str = (format_str % dict(location=conf['location'],
                                           project=project,
                                           time=time_str))
            if set_adium_status(adium_str + blurb, away):
                log.info('Updated Adium status to: %s' % adium_str)
            else:
                log.info("Couldn't update Adium status")


@command('clockin')
class ClockinCommand(ActionCommand):

    description = 'Start logging hours to a project'

    def add_arguments(self, parser):
        parser.add_argument('project', type=str, action='store', default=None, nargs='?')
        super(ClockinCommand, self).add_arguments(parser)

    def execute(self, args):
        project, clockin_time = self.clocked_in_info()
        if project:
            commands['clockout'].execute(args, allow_adium_update=False)

        clockin_time = parse_date(args.time) if args.time else now
        clockin_project = args.project or last_project()
        if not clockin_project:
            log.error('You must specify a project for your first clockin.')
            return

        write_clockin(clockin_project, clockin_time)

        log.info('Clocked into %s at %s' % (
            clockin_project, clockin_time.strftime(user_date_format)))

        self.update_adium(adium_clockin_fmt, clockin_project, clockin_time, args.away)


@command('clockout')
class ClockoutCommand(ActionCommand):
    
    description = 'Stop logging hours to a project'

    def execute(self, args, allow_adium_update=True):
        clockout_time = parse_date(args.time) if args.time else now

        project, clockin_time = self.clocked_in_info()

        if not project:
            log.info('Not clocked into anything. Clockout failed.')
            return

        if clockout_time < clockin_time:
            log.info('Clockout time is before last clockin time. Clockout failed.')
            return

        write_clockout(clockout_time)

        log.info('Clocked out of %s at %s' % (
            project, clockout_time.strftime(user_date_format)))

        if allow_adium_update:
            self.update_adium(adium_clockout_fmt, project, clockout_time, args.away)


@command('toggle')
class ToggleCommand(ActionCommand):

    description = 'Clock in or out of the most recent project'

    def execute(self, args):
        project, clockin_time = self.clocked_in_info()

        if project:
            commands['clockout'].execute(args)
        else:
            args.project = None
            commands['clockin'].execute(args)


@command('summary')
class SummaryCommand(Command):

    description = 'Count hours spent on a project'

    def add_arguments(self, parser):
        parser.add_argument('project', type=str, action='store',  nargs='*')

        parser.add_argument('-m', '--more-projects', type=str, dest='more_projects',
                            action='store', nargs='+', default=[])

        parser.add_argument('--from', dest='tfrom', type=str, action='store',
                            default=None, help='When to start counting')

        parser.add_argument('--to', dest='tto', type=str, action='store',
                            default=None, help='When to stop counting')

    def _format_timedelta(self, timedelta):
        hours, minutes = hours_and_minutes_from_seconds(timedelta.seconds)
        min_str = 'minute' if minutes == 1 else 'minutes'
        if hours == 0:
            return '%d %s' % (minutes, min_str)
        else:
            hour_str = 'hour' if hours == 1 else 'hours'
            return '%d %s, %d %s' % (hours, hour_str, minutes, min_str)

    def execute(self, args):
        proj = ' '.join(args.project)
        if proj:
            projects = [proj] + args.more_projects
        else:
            projects = args.more_projects
        if not projects:
            projects = None

        from_time, to_time = parse_date_range_args(args.tfrom, args.tto)

        for file_path in util.all_files():
            print os.path.split(os.path.splitext(file_path)[0])[1]

            from_time, to_time = self.find_file_min_max(file_path,
                                                        from_time, to_time,
                                                        projects)
            min_day = datetime.datetime(year=from_time.year,
                                        month=from_time.month,
                                        day=from_time.day)

            project_sums, total_time = self.file_summary(file_path,
                                                         from_time, to_time,
                                                         projects)

            for name in sorted(project_sums.keys()):
                log.info(name)

                # { 2011: {0: [(datetime, timedelta)]}}
                months = defaultdict(list)
                for d_day in xrange((to_time-from_time).days+1):
                    today = min_day + datetime.timedelta(days=d_day)
                    today_min = max(today, from_time)
                    today_max = min(today + datetime.timedelta(days=1), to_time)
                    project_sum, _ = self.file_summary(file_path, today_min, today_max, [name])
                    timedelta = project_sum[name]
                    if timedelta > datetime.timedelta(0):
                        months[(today.year, today.month)].append((today, project_sum[name]))

                if len(months) > 1:
                    for month_tuple, days in sorted(months.items()):
                        log.info(days[0][0].strftime('  %B %Y'))
                        self.print_days(days, 4)
                else:
                    self.print_days(years.values()[0], 2)

                log.info('  Total: %s' % self._format_timedelta(project_sums[name]))

            if project_sums:
                log.info('')

            log.info('Total: %s' % self._format_timedelta(total_time))

    def print_days(self, days, indent=2):
        for day, timedelta in days:
            time_str = self._format_timedelta(timedelta)
            log.info(day.strftime(' '*indent + '%%Y-%%m-%%d: %s' % time_str))

    def find_file_min_max(self, file_path, from_time, to_time, projects):
        min_datetime = None
        max_datetime = None
        with open(file_path, 'r') as f:
            for line in f:
                this_proj, clockin_time = parse_clockin(line)
                if projects is None or this_proj in projects:
                    if min_datetime is None:
                        min_datetime = clockin_time
                    else:
                        min_datetime = min(min_datetime, clockin_time)
                    try:
                        clockout_time = parse_clockout(f.next())
                    except StopIteration:
                        clockout_time = now
                    if max_datetime is None:
                        max_datetime = clockout_time
                    else:
                        max_datetime = max(max_datetime, clockout_time)
        if None in (min_datetime, max_datetime):
            return now, now
        else:
            return min_datetime, max_datetime

    def file_summary(self, file_path, from_time, to_time, projects):
        project_sums = defaultdict(lambda: datetime.timedelta())
        total_time = datetime.timedelta()
        with open(file_path, 'r') as f:
            for line in f:
                this_proj, clockin_time = parse_clockin(line)
                if projects is None or this_proj in projects:
                    try:
                        clockout_time = parse_clockout(f.next())
                    except StopIteration:
                        clockout_time = now
                    time_in_range = self.time_in_range(clockin_time, clockout_time,
                                                       from_time, to_time)
                    project_sums[this_proj] += time_in_range
                    total_time += time_in_range
        return project_sums, total_time

    def time_in_range(self, clockin_time, clockout_time, from_time, to_time):
        if from_time is not None:
            if clockout_time <= from_time:
                return datetime.timedelta(0)
            clockin_time = max(clockin_time, from_time)

        if to_time is not None:
            if clockin_time >= to_time:
                return datetime.timedelta(0)
            clockout_time = min(clockout_time, to_time)

        return clockout_time - clockin_time
