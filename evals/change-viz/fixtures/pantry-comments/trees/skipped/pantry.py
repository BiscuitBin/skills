#!/usr/bin/env python3
"""Print the total count of each item in a pantry list."""

import sys


def read_records(lines):
    """Yield each line that holds a record, skipping blank lines and # comments."""
    for line in lines:
        text = line.strip()
        if text and not text.startswith("#"):
            yield text


def parse_line(line):
    name, count = line.split("|")
    return name.strip(), int(count)


def sum_counts(lines):
    totals = {}
    for line in read_records(lines):
        name, count = parse_line(line)
        totals[name] = totals.get(name, 0) + count
    return totals


def main(argv):
    if len(argv) != 2:
        print("usage: pantry.py FILE", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        totals = sum_counts(handle)
    for name in sorted(totals):
        print(f"{name}: {totals[name]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
