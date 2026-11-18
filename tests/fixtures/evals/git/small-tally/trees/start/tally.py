#!/usr/bin/env python3
"""Print the total of the numbers in a text file, one number per line."""

import sys


def total(lines):
    return sum(float(line) for line in lines)


def main(argv):
    if len(argv) != 2:
        print("usage: tally.py FILE", file=sys.stderr)
        return 2
    with open(argv[1]) as handle:
        print(f"total: {total(handle):g}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
