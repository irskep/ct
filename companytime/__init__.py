#!/usr/bin/python

import argparse
import logging
import os
import sys

from companytime.commands import commands
from companytime.util import load_config

logging.basicConfig(level=logging.INFO, format="%(message)s")

log = logging.getLogger('companytime.main')

def main():
    home_ct = os.path.join(os.environ['HOME'], '.ct')
    if 'CT_HOME' not in os.environ or not os.path.isdir(os.environ['CT_HOME']):
        if not os.path.isdir(home_ct):
            log.info('Creating ~/.ct')
            os.mkdir(home_ct)
        os.environ['CT_HOME'] = os.path.join(os.environ['HOME'], '.ct')

    parser = argparse.ArgumentParser(prog='ct',
                                     description='Time tracking tool')

    subparsers = parser.add_subparsers(title='subcommands',
                                       help='Type "ct [command] --help" for more information.')

    for name, cmd in commands.viewitems():
        new_parser = subparsers.add_parser(name, description=cmd.description)
        new_parser.add_argument('--config', default=False, action='store_true',
                                dest='config', help='update configuration options')
        cmd.add_arguments(new_parser)
        new_parser.set_defaults(func=cmd.execute)

    parser.add_argument('--config', default=False, action='store_true',
                        dest='config', help='update configuration options')

    args = parser.parse_args()
    if args.config:
        load_config(reset=True)
    args.func(args)

if __name__ == '__main__':
    main()
