#!/usr/bin/env python3
"""Print word statistics for a text file."""

import argparse
import string
import sys
from collections import Counter


def words(text):
    """The words in the text, lower-cased, with punctuation stripped from each end."""
    found = (token.strip(string.punctuation).lower() for token in text.split())
    return [word for word in found if word]


def most_common(found, count):
    """The count most frequent words with their counts, most frequent first."""
    return Counter(found).most_common(count)


def main(argv):
    parser = argparse.ArgumentParser(prog="wordstat.py")
    parser.add_argument("file")
    parser.add_argument("--top", type=int, metavar="N", help="also list the N most common words")
    args = parser.parse_args(argv[1:])
    with open(args.file, encoding="utf-8") as handle:
        found = words(handle.read())
    print(f"words: {len(found)}")
    print(f"distinct: {len(set(found))}")
    if args.top:
        print("most common:")
        for word, times in most_common(found, args.top):
            print(f"  {word} {times}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
