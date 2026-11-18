#!/usr/bin/env python3
"""Summarise a log of hikes kept in a CSV file."""

import argparse
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
    parser = argparse.ArgumentParser(prog="hikes.py")
    parser.add_argument("file")
    parser.add_argument("--longest", action="store_true", help="also name the longest hike")
    parser.add_argument("--year", help="count only the hikes from this year, such as 2025")
    args = parser.parse_args(argv[1:])
    hikes = read_hikes(args.file)
    if args.year:
        hikes = [hike for hike in hikes if hike["date"].startswith(f"{args.year}-")]
    print(f"hikes: {len(hikes)}")
    print(f"total: {sum(hike['km'] for hike in hikes):.1f} km")
    if args.longest and hikes:
        longest = max(hikes, key=lambda hike: hike["km"])
        print(f"longest: {longest['trail']}, {longest['km']:.1f} km on {longest['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
