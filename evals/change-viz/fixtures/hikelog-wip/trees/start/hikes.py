#!/usr/bin/env python3
"""Summarise a log of hikes kept in a CSV file."""

import csv
import sys


def read_hikes(path):
    """The hikes in the log, oldest first, each with its date, trail and distance in km."""
    with open(path, newline="", encoding="utf-8") as handle:
        return [
            {"date": row["date"], "trail": row["trail"], "km": float(row["km"])}
            for row in csv.DictReader(handle)
        ]


def main(argv):
    if len(argv) != 2:
        print("usage: hikes.py FILE", file=sys.stderr)
        return 2
    hikes = read_hikes(argv[1])
    print(f"hikes: {len(hikes)}")
    print(f"total: {sum(hike['km'] for hike in hikes):.1f} km")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
