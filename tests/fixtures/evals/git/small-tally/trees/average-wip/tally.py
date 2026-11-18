#!/usr/bin/env python3
"""Print the total and the average of the numbers in a text file, one number per line."""

import sys


def numbers(lines):
    return [float(line) for line in lines if line.strip()]


def total(lines):
    return sum(numbers(lines))


def average(lines):
    values = numbers(lines)
    return sum(values) / len(values)


def main(argv):
    if len(argv) != 2:
        print("usage: tally.py FILE", file=sys.stderr)
        return 2
    with open(argv[1]) as handle:
        lines = handle.readlines()
    print(f"total: {total(lines):g}")
    print(f"average: {average(lines):g}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
