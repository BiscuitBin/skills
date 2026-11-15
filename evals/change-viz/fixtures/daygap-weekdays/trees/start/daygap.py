#!/usr/bin/env python3
"""Print how many days lie between two dates."""

import argparse
import sys
from datetime import date


def days_between(start, end):
    """Whole days from start to end, negative when end comes first."""
    return (end - start).days


def main(argv=None):
    parser = argparse.ArgumentParser(prog="daygap", description=__doc__)
    parser.add_argument("start", type=date.fromisoformat, help="the first date, as YYYY-MM-DD")
    parser.add_argument("end", type=date.fromisoformat, help="the second date, as YYYY-MM-DD")
    args = parser.parse_args(argv)
    print(f"{days_between(args.start, args.end)} days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
