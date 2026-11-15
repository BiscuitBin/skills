#!/usr/bin/env python3
"""Print a short fingerprint of each text file, or check files against recorded ones."""

import argparse
import hashlib
import sys


def fingerprint(text):
    """The first 12 hex digits of the SHA-256 of the text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def fingerprint_file(path):
    with open(path, encoding="utf-8") as handle:
        return fingerprint(handle.read())


def check(listing):
    """Compare each file named in the listing with its recorded fingerprint."""
    with open(listing, encoding="utf-8") as handle:
        entries = [line.split(None, 1) for line in handle if line.strip()]
    mismatches = 0
    for recorded, name in entries:
        path = name.strip()
        now = fingerprint_file(path)
        if now == recorded:
            print(f"{path}: OK")
        else:
            print(f"{path}: FAILED (recorded {recorded}, now {now})")
            mismatches += 1
    if mismatches:
        print(f"{mismatches} of {len(entries)} fingerprints did not match")
        return 1
    return 0


def main(argv):
    parser = argparse.ArgumentParser(prog="fingerprint.py")
    parser.add_argument("files", nargs="*", metavar="FILE")
    parser.add_argument("--check", metavar="LIST", help="compare with the fingerprints in LIST")
    args = parser.parse_args(argv[1:])
    if args.check:
        return check(args.check)
    if not args.files:
        parser.error("give at least one FILE, or --check LIST")
    for path in args.files:
        print(f"{fingerprint_file(path)}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
