#!/usr/bin/env python3
"""Print a short fingerprint of each text file."""

import hashlib
import sys


def fingerprint(text):
    """The first 12 hex digits of the SHA-256 of the text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def main(argv):
    if len(argv) < 2:
        print("usage: fingerprint.py FILE...", file=sys.stderr)
        return 2
    for path in argv[1:]:
        with open(path, encoding="utf-8") as handle:
            print(f"{fingerprint(handle.read())}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
