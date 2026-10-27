"""Validate eval cases, or run them against an agent. See docs/reference/evals.md."""

import argparse
import sys
from pathlib import Path

from skills_tooling.evals.cases import validate_all


def validate(root: Path) -> int:
    problems = validate_all(root)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    count = len(list((root / "evals").glob("*/evals.json")))
    print(f"{count} eval suite{'' if count == 1 else 's'} valid.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m skills_tooling.evals", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate every evals/*/evals.json.")
    check.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    sys.exit(validate(args.root))


if __name__ == "__main__":
    main()
