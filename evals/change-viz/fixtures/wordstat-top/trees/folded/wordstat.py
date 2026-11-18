#!/usr/bin/env python3
"""Print word statistics for a text file."""

import string
import sys


def words(text):
    """The words in the text, lower-cased, with punctuation stripped from each end."""
    found = (token.strip(string.punctuation).lower() for token in text.split())
    return [word for word in found if word]


def main(argv):
    if len(argv) != 2:
        print("usage: wordstat.py FILE", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        found = words(handle.read())
    print(f"words: {len(found)}")
    print(f"distinct: {len(set(found))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
