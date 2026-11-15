#!/usr/bin/env python3
"""Replay a lending desk's event log and print the state of each copy."""

import sys
from datetime import date

from lending.events import replay


def is_overdue(copy, today):
    """Whether a copy on loan is late back on the given day."""
    return copy["state"] == "on_loan" and today >= copy["due"]


def report(copies, today):
    """One line per copy, in id order, with late loans marked."""
    lines = []
    for copy_id in sorted(copies):
        copy = copies[copy_id]
        line = f"{copy_id} {copy['state']}"
        if copy["state"] == "on_loan":
            line += f" {copy['member']} due {copy['due']}"
            if is_overdue(copy, today):
                line += " OVERDUE"
        lines.append(line)
    return lines


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
