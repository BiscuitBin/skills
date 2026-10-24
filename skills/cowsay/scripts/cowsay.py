"""Render a talking cow using only the Python 3 standard library."""

import argparse
import sys
import textwrap

WIDTH = 40
COW = "    \\   ^__^\n     \\  (oo)\\_______\n        (__)\\       )\\/\\\n            ||----w |\n            ||     ||\n"


def render(text: str) -> str:
    """Wrap at 40 code points, retaining explicit line breaks and blank lines."""
    lines = [part for line in text.split("\n") for part in (textwrap.wrap(line, WIDTH) or [""])]
    width = max(map(len, lines))
    bubble = [" " + "_" * (width + 2)]
    for index, line in enumerate(lines):
        if len(lines) == 1:
            left, right = "<", ">"
        elif index == 0:
            left, right = "/", "\\"
        elif index == len(lines) - 1:
            left, right = "\\", "/"
        else:
            left, right = "|", "|"
        bubble.append(f"{left} {line.ljust(width)} {right}")
    bubble.append(" " + "-" * (width + 2))
    return "\n".join(bubble) + "\n" + COW


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", help="Text to say; omitted reads UTF-8 stdin.")
    args = parser.parse_args()
    text = args.text if args.text is not None else sys.stdin.buffer.read().decode("utf-8")
    sys.stdout.buffer.write(render(text).encode("utf-8"))


if __name__ == "__main__":
    main()
