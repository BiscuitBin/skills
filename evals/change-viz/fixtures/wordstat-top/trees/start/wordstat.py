#!/usr/bin/env python3
"""Print word statistics for a text file."""

import sys


def words(text):
    return text.split()


def main(argv):
    if len(argv) != 2:
        print("usage: wordstat.py FILE", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        found = words(handle.read())
    print(f"words: {len(found)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
