#!/usr/bin/env python3
"""Print the total count of each item in a pantry list."""

import sys


class RecordError(ValueError):
    """A line that is not in the name|count form."""


def read_records(lines):
    """Yield (number, text) for each line that holds a record.

    Blank lines and # comments are skipped, but still counted, so a number is
    the line's place in the file.
    """
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if text and not text.startswith("#"):
            yield number, text


def parse_line(text, number):
    fields = text.split("|")
    if len(fields) != 2:
        raise RecordError(f'line {number}: expected "name|count", got {text!r}')
    name, count = fields
    return name.strip(), int(count)


def sum_counts(lines):
    totals = {}
    for number, text in read_records(lines):
        name, count = parse_line(text, number)
        totals[name] = totals.get(name, 0) + count
    return totals


def main(argv):
    if len(argv) != 2:
        print("usage: pantry.py FILE", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as handle:
            totals = sum_counts(handle)
    except RecordError as error:
        print(f"pantry.py: {error}", file=sys.stderr)
        return 1
    for name in sorted(totals):
        print(f"{name}: {totals[name]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
