#!/usr/bin/env python3
"""Replay a lending desk's event log and print the state of each copy."""

import sys
from datetime import date

from lending.events import replay
from lending.report import report


def main(argv):
    if len(argv) != 3:
        print("usage: desk.py EVENTS DATE", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        copies = replay(handle)
    for line in report(copies, date.fromisoformat(argv[2])):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
