#!/usr/bin/python

from argparse import ArgumentParser
from collections import defaultdict
import datetime
import logging
import os

from dateutil.parser import parse as parse_date

from companytime.util import all_files, file_for_current_user, hours_and_minutes_from_seconds, init, now, parse_clockin, parse_clockout, parse_date_range_args, writeln, write_clockin, write_clockout

user_date_format = '%I:%M %p on %b %d, %Y'

log = logging.getLogger('companytime.commands')


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
        f = file_for_current_user()
        if f:
            last_line = f.readlines()[-1]
            if 'clockin' in last_line:
                return parse_clockin(last_line)
            else:
                return None, None
        else:
            return None, None


@command('clockin')
class ClockinCommand(Command):

    description = 'Start logging hours to a project'

    def add_arguments(self, parser):
        parser.add_argument('project', type=str, 
                            action='store',  nargs='+')

        parser.add_argument('-t', '--time', type=unicode, dest='time',
                            action='store', default=None,
                            help='Time to log for checkin')

    def execute(self, args):
        proj = ' '.join(args.project)

        project, clockin_time = self.clocked_in_info()
        if project:
            commands['clockout'].execute(args)

        clockin_time = parse_date(args.time) if args.time else now

        write_clockin(proj, clockin_time)

        log.info('Clocked into %s at %s' % (
            proj, clockin_time.strftime(user_date_format)))


@command('clockout')
class ClockoutCommand(Command):
    
    description = 'Stop logging hours to a project'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--time', type=unicode, action='store',
                            default=None, dest='time',
                            help='Time to log for checkin')

    def execute(self, args):
        clockout_time = parse_date(args.time) if args.time else now

        project, clockin_time = self.clocked_in_info()

        if project:
            if clockout_time >= clockin_time:
                write_clockout(clockout_time)

                log.info('Clocked out of %s at %s' % (
                    project, clockout_time.strftime(user_date_format)))
            else:
                log.info('Clockout time is before last clockin time. Clockout failed.')
        else:
            log.info('Not clocked into anything. Clockout failed.')


@command('summary')
class SummaryCommand(Command):

    description = 'Count hours spent on a project'

    def add_arguments(self, parser):
        parser.add_argument('project', type=str, action='store',  nargs='*')

        parser.add_argument('-m', '--more-projects', type=str, dest='more_projects',
                            action='store', nargs='+', default=[])

        parser.add_argument('-f', dest='tfrom', type=str, action='store',
                            default=None, help='When to start counting')

        parser.add_argument('-t', dest='tto', type=str, action='store',
                            default=None, help='When to stop counting')

        parser.add_argument('-v', '--verbose', action='store_const',
                            const=True, default=False)

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

        total_time = datetime.timedelta()

        project_sums = defaultdict(lambda: datetime.timedelta())

        for file in all_files('r'):
            with file as f:
                lines = f.readlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                this_proj, clockin_time = parse_clockin(line)
                if i == len(lines)-1:
                    clockout_time = now
                else:
                    clockout_time = parse_clockout(lines[i+1])
                if projects is None or this_proj in projects:
                    if from_time is None or clockin_time >= from_time:
                        if to_time is None or clockout_time <= to_time:
                            dt = clockout_time - clockin_time
                            project_sums[this_proj] += dt
                            total_time += dt
                i += 2

        for name in sorted(project_sums.keys()):
            log.info('%s: %s' % (name, self._format_timedelta(project_sums[name])))
        
        if project_sums:
            log.info('')

        log.info('Total: %s' % self._format_timedelta(total_time))

        if from_time or to_time != now:
            log.info("Periods are only counted if their start *and* end times are within the given range.")
