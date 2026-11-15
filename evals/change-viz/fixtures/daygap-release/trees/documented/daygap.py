#!/usr/bin/env python3
"""Print how many days lie between two dates."""

import argparse
import sys
from datetime import date, timedelta


def days_between(start, end):
    """Whole days from start to end, negative when end comes first."""
    return (end - start).days


def weekdays_between(start, end):
    """Days from start up to, but not including, end that fall on Monday to Friday.

    Negative when end comes first, like days_between.
    """
    if end < start:
        return -weekdays_between(end, start)
    return sum(1 for n in range((end - start).days) if (start + timedelta(days=n)).weekday() < 5)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="daygap", description=__doc__)
    parser.add_argument("start", type=date.fromisoformat, help="the first date, as YYYY-MM-DD")
    parser.add_argument("end", type=date.fromisoformat, help="the second date, as YYYY-MM-DD")
    parser.add_argument(
        "--weekdays",
        action="store_true",
        help="also print how many of the days fall on Monday to Friday",
    )
    args = parser.parse_args(argv)
    print(f"{days_between(args.start, args.end)} days")
    if args.weekdays:
        print(f"{weekdays_between(args.start, args.end)} weekdays")
    return 0


if __name__ == "__main__":
    sys.exit(main())
