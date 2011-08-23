#!/usr/bin/python

import argparse
import logging
import os
import sys

from companytime.commands import commands

logging.basicConfig(level=logging.INFO, format="%(message)s")

log = logging.getLogger('companytime.main')

def main():
    if 'CT_HOME' not in os.environ:
        log.error('Create a working directory (e.g. ~/.ct) and point $CT_HOME at it.')
        sys.exit(1)

    parser = argparse.ArgumentParser(prog='ct',
                                     description='Time tracking tool')

    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='additional help')

    for name, cmd in commands.viewitems():
        new_parser = subparsers.add_parser(name,
                                           description=cmd.description)
        cmd.add_arguments(new_parser)
        new_parser.set_defaults(func=cmd.execute)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
