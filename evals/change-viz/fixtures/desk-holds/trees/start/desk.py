#!/usr/bin/env python3
"""Replay a lending desk's event log and print the state of each copy."""

import sys
from datetime import date


def parse(line):
    """One event line: its date, its action and the fields after them."""
    day, action, *fields = line.split()
    return date.fromisoformat(day), action, fields


def replay(lines):
    """Each copy's state after every event in the log, by copy id."""
    copies = {}
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        day, action, fields = parse(line)
        copy = copies.setdefault(fields[0], {"state": "available", "member": None, "due": None})
        if action == "lend":
            if copy["state"] != "available":
                raise ValueError(f"{day}: {fields[0]} is {copy['state']}")
            copy.update(state="on_loan", member=fields[1], due=date.fromisoformat(fields[2]))
        elif action == "return":
            copy.update(state="available", member=None, due=None)
        else:
            raise ValueError(f"{day}: unknown action {action!r}")
    return copies


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
