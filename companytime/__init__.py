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
    parser.add_argument('command', type=str, action='store',
                        choices=commands.keys(),
                        help='init, clockin, or clockout')
    args = parser.parse_args(sys.argv[1:2])
    commands[args.command](sys.argv[2:])

if __name__ == '__main__':
    main()
