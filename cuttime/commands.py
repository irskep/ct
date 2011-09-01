#!/usr/bin/python

from argparse import ArgumentParser
import calendar
from collections import defaultdict
import datetime
import logging
from math import ceil
import os

from dateutil.parser import parse as parse_date

from cuttime import util
from cuttime.util import file_for_current_user, hours_and_minutes, last_project, load_config, now, parse_clockin, parse_clockout, parse_date_range_args, set_adium_status, writeln, write_clockin, write_clockout

user_date_format = '%I:%M %p on %b %d, %Y'

log = logging.getLogger('cuttime.commands')

adium_clockin_fmt = 'At %(location)s working on %(project)s. (updated %(time)s)'
adium_clockout_fmt = 'Not currently tracking time. Last seen at %(location)s working on %(project)s. (updated %(time)s)'
blurb = '\n\nThis message brought to you by ct (github.com/irskep/ct)'


commands = {}

def command(name):
    """Declare a command"""
    def dec(cls):
        commands[name] = cls
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
            commands['clockout']().execute(args, allow_adium_update=False)

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
            commands['clockout']().execute(args)
        else:
            args.project = None
            commands['clockin']().execute(args)


@command('summary')
class SummaryCommand(Command):

    description = 'Count hours spent on a project'

    def __init__(self, *args, **kwargs):
        super(SummaryCommand, self).__init__(*args, **kwargs)
        self.format_funcs = dict(pretty=self.print_file_pretty,
                                 weekly=self.print_file_weekly,
                                 csv=self.print_file_csv)

    def add_arguments(self, parser):
        parser.add_argument('project', type=str,
                            action='store',  nargs='*')

        parser.add_argument('--from', dest='tfrom', type=str, action='store',
                            default=None, help='When to start counting')

        parser.add_argument('--to', dest='tto', type=str, action='store',
                            default=None, help='When to stop counting')

        parser.add_argument('--format', dest='format', choices=['pretty', 'weekly', 'csv'],
                            default='pretty')
        
        parser.add_argument('--week', dest='week', default=False, action='store_true')

    def _format_timedelta(self, timedelta):
        hours, minutes = hours_and_minutes(timedelta)
        min_str = 'minute' if minutes == 1 else 'minutes'
        if hours == 0:
            return '%d %s' % (minutes, min_str)
        else:
            hour_str = 'hour' if hours == 1 else 'hours'
            return '%d %s, %d %s' % (hours, hour_str, minutes, min_str)

    def execute(self, args):
        projects = args.project or None
        from_time, to_time = parse_date_range_args(args.tfrom, args.tto)

        if args.week:
            from_time_date = self._week_for_day(now)[0]
            print from_time_date
            from_time = datetime.datetime(year=from_time_date.year,
                                          month=from_time_date.month,
                                          day=from_time_date.day)
            format_func = self.print_file_weekly
        else:
            format_func = self.format_funcs[args.format]

        for file_path in util.all_files():
            print os.path.split(os.path.splitext(file_path)[0])[1]

            format_func(file_path, from_time, to_time, projects)

    def _daily_times(self, file_path, from_time, to_time, projects):
        """Yield a (day, timedelta) tuple for each day in {from_time...to_time} with
        more than zero hours that is billed to one of *projects*
        """
        min_day = datetime.datetime(year=from_time.year,
                                    month=from_time.month,
                                    day=from_time.day)
        delta = to_time - from_time
        num_days = delta.days + int(ceil(delta.seconds/float(24*60*60)))
        for d_day in xrange(num_days + 1):
            today = min_day + datetime.timedelta(days=d_day)
            today_min = max(today, from_time)
            today_max = min(today + datetime.timedelta(days=1), to_time)

            project_sums, _ = self.file_summary(file_path, today_min, today_max, projects)

            timedelta = reduce(lambda a, b: a+b, project_sums.values(), datetime.timedelta(0))
            if timedelta > datetime.timedelta(0):
                yield (today, timedelta)

    def _week_for_day(self, day):
        weeks = calendar.Calendar().monthdatescalendar(day.year, day.month)
        for week in weeks:
            # calendar module starts weeks at Monday, we want Sunday
            week = [week[0] - datetime.timedelta(days=1)] + week[0:-1]
            if day.date() in week:
                return week

    def _timedelta_to_hours(self, timedelta, round_to_quarters=True):
        hours = timedelta.days*24 + timedelta.seconds/3600.0
        if round_to_quarters:
            hours = round(hours*4)/4
        return hours

    def print_file_pretty(self, file_path, from_time, to_time, projects):
        projects, from_time, to_time = self._file_data(file_path, from_time, to_time, projects)

        project_sums, total_time = self.file_summary(file_path,
                                                     from_time, to_time,
                                                     projects)

        for name in sorted(projects):
            log.info(name)

            # { 2011: {0: [(datetime, timedelta)]}}
            months = defaultdict(list)
            for day, timedelta in self._daily_times(file_path, from_time, to_time, [name]):
                months[(day.year, day.month)].append((day, timedelta))

            if len(months) > 1:
                for month_tuple, days in sorted(months.items()):
                    log.info(days[0][0].strftime('  %B %Y'))
                    self.print_days(days, 4)
            else:
                self.print_days(months.values()[0], 2)

            log.info('  Total: %s' % self._format_timedelta(project_sums[name]))

        if project_sums:
            log.info('')

        log.info('Total: %s' % self._format_timedelta(total_time))

    def print_file_weekly(self, file_path, from_time, to_time, projects):
        projects, from_time, to_time = self._file_data(file_path, from_time, to_time, projects)
        current_week = None
        weekly_total = datetime.timedelta()
        for day, timedelta in self._daily_times(file_path, from_time, to_time, projects):
            if current_week is None or day.date() not in current_week:
                if current_week:
                    log.info('Total: %0.2f\n' %
                             self._timedelta_to_hours(weekly_total))
                    weekly_total = datetime.timedelta()
                current_week = self._week_for_day(day)
                log.info('%s to %s' %
                         (current_week[0].strftime('%Y-%m-%d'),
                          current_week[-1].strftime('%Y-%m-%d')))
            log.info('  %s: %0.2f' % ((day.strftime('%a'),
                                       self._timedelta_to_hours(timedelta))))
            weekly_total += timedelta
        if current_week:
            log.info('Total: %0.2f' %
                     self._timedelta_to_hours(weekly_total))
            weekly_total = datetime.timedelta()
            

    def print_file_csv(self, file_path, from_time, to_time, projects):
        projects, from_time, to_time = self._file_data(file_path, from_time, to_time, projects)
        for day, timedelta in self._daily_times(file_path, from_time, to_time, projects):
            log.info(', '.join((day.strftime('%Y-%m-%d'),
                                '%0.2f' % self._timedelta_to_hours(timedelta))))

    def print_days(self, days, indent=2):
        for day, timedelta in days:
            time_str = self._format_timedelta(timedelta)
            log.info(day.strftime(' '*indent + '%%Y-%%m-%%d: %s' % time_str))

    def _file_data(self, file_path, from_time=None, to_time=None, projects=None):
        """Given a file and user-supplied parameters, return (projects, from_time, to_time),
        where projects is a set, and from_time and to_time are datetime objects. No return
        value will be None.
        """
        scraped_projects = set()
        min_datetime = None
        max_datetime = None
        with open(file_path, 'r') as f:
            for line in f:
                this_proj, clockin_time = parse_clockin(line)
                if projects is None or this_proj in projects:
                    scraped_projects.add(this_proj)

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
            new_from, new_to = now, now
        else:
            new_from, new_to = min_datetime, max_datetime
        if from_time is None or new_from > from_time:
            from_time = new_from
        if to_time is None or new_to < to_time:
            to_time = new_to
        return scraped_projects, from_time, to_time

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
