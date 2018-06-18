import argparse
import importlib
import os
from .spaces import Slack


def spaces(s):
    try:
        m, c = s.rsplit('.', 1)
        return getattr(importlib.import_module(m), c)
    except:
        raise argparse.ArgumentTypeError('Unknown space')


def parse():
    prog = os.path.basename(os.path.dirname(__file__))
    parser = argparse.ArgumentParser(prog, description='A bot engine')
    parser.add_argument('--space',
                        type=spaces,
                        default=Slack,
                        help='Space name')
    parser.add_argument('--token',
                        required=True,
                        help='Space auth token')
    parser.add_argument('--modules',
                        nargs='*',
                        default=['bot.modules'],
                        metavar='MODULE',
                        help='Bot modules')
    parser.add_argument('--errorsto',
                        help='Error destination')
    return parser.parse_args()
